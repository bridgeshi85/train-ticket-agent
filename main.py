import json

from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import StructuredTool, render_text_description

from core.agent import MyAgent, ActionModel
from tools.train_ticket_query import search_train_ticket_tool
from tools.finish import finish_tool

load_dotenv()

if __name__ == "__main__":
    tools = [search_train_ticket_tool, finish_tool]
    with open("prompts/task_prompt.txt", "r", encoding="utf-8") as f:
        prompt_text = f.read()

    with open("prompts/final_prompt.txt", "r", encoding="utf-8") as f:
        final_prompt_text = f.read()

    # 构建提示词模板（PromptTemplate） ← 你在 main.py 中做这件事
    parser = PydanticOutputParser(pydantic_object=ActionModel)
    prompt = PromptTemplate.from_template(prompt_text).partial(
        tools=render_text_description(tools),
        format_instructions=json.dumps(
            parser.get_format_instructions(), ensure_ascii=False
        )
    )

    my_agent = MyAgent(
        llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0),
        tools=tools,
        prompt=prompt,
        final_prompt=final_prompt_text,
    )

    task = "帮我查询2025年6月10日去南京的火车票"
    reply = my_agent.run(task)
