import openai
import json, ast
import os
import chainlit as cl
import autogen

MAX_ITER = 5


@cl.on_chat_start
async def setup_agent():
    config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST")
    # create an AssistantAgent named "assistant"
    assistant = autogen.AssistantAgent(
                    name="assistant",
                    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE") or x.get("content", "").strip() == "",
                    llm_config={
                        "seed": 42,  # seed for caching and reproducibility
                        "config_list": config_list,  # a list of OpenAI API configurations
                        "temperature": 0,  # temperature for sampling
                    },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
                    )
    cl.user_session.set('assistant', assistant)
    # create a UserProxyAgent instance named "user_proxy"
    user_proxy = autogen.UserProxyAgent(
                        name="user_proxy",
                        human_input_mode="NEVER",
                        max_consecutive_auto_reply=1,
                        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE") or x.get("content", "").strip() == "",
                        code_execution_config={
                            "work_dir": "coding",
                            "use_docker": False,  # set to True or image name like "python:3" to use docker
                        },
                    )
    cl.user_session.set('user_proxy', user_proxy)
    await cl.Message(content=f"Start chatting with code interpreter").send()

@cl.on_file_upload(accept=["text/plain"], max_files=3, max_size_mb=2)
async def upload_file(files: any):
    """
    Handle uploaded files.

    Args:
        files (list): List of uploaded file data.

    Example:
        [{
            "name": "example.txt",
            "content": b"File content as bytes",
            "type": "text/plain"
        }]
    """
    for file_data in files:
        file_name = file_data["name"]
        content = file_data["content"]
        # If want to show content Content: {content.decode('utf-8')}\n\n
        await cl.Message(content=f"Uploaded file: {file_name}\n").send()
        
        # Save the file locally
        with open(file_name, "wb") as file:
            file.write(content)



@cl.on_message
async def run_conversation(user_message: str):
    print('CONVERSATION')
    # check if user message changed
    if user_message == cl.user_session.get('user_message'):
        return
    assistant = cl.user_session.get('assistant')
    user_proxy = cl.user_session.get('user_proxy')
    cur_iter = 0
    while cur_iter < MAX_ITER:
        if len(assistant.chat_messages[user_proxy]) == 0 :
            print('initiating chat')
            user_proxy.initiate_chat(
                assistant,
                message=user_message,
            )
        else:
            print('FOLLOW up message')
            # followup of the previous question
            user_proxy.send(
                recipient=assistant,
                message=user_message,
            )
        message_history = assistant.chat_messages[user_proxy]
        last_seen_message_index = cl.user_session.get('last_seen_message_index', 0)
        print(message_history)
        for message in message_history[last_seen_message_index+1:]:
            await cl.Message(author=message["role"], content=message["content"]).send()
        cl.user_session.set('last_seen_message_index', len(message_history))

        cur_iter += 1
        return