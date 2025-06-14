# core/agent.py

import json
import sys
from typing import Optional, Tuple, Dict, Any
from uuid import UUID

from pydantic import ValidationError, BaseModel, Field
from langchain.memory import ConversationTokenBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import GenerationChunk, ChatGenerationChunk, LLMResult
from langchain_core.callbacks import BaseCallbackHandler

from langchain.tools.render import render_text_description


class ActionModel(BaseModel):
    name: str = Field(description="工具或指令名称")
    args: Optional[Dict[str, Any]] = Field(description="工具或指令参数，由参数名称和参数值组成")


class MyPrintHandler(BaseCallbackHandler):
    """自定义 CallbackHandler，用于打印 LLM 推理过程"""

    def on_llm_new_token(
            self,
            token: str,
            *,
            chunk: Optional[GenerationChunk] = None,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        sys.stdout.write(token)
        sys.stdout.flush()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        sys.stdout.write("\n")
        sys.stdout.flush()
        return response


class MyAgent:
    def __init__(
            self,
            llm: BaseChatModel,
            tools: list,
            prompt: PromptTemplate,
            final_prompt: str,
            max_thought_steps: Optional[int] = 3,
    ):
        self.llm = llm
        # self.tools = tools
        # Convert tool list to dict for fast lookup by name
        self.tools = {tool.name: tool for tool in tools}
        self.max_thought_steps = max_thought_steps
        self.output_parser = PydanticOutputParser(pydantic_object=ActionModel)
        self.final_prompt = PromptTemplate.from_template(final_prompt)
        self.llm_chain = prompt | self.llm | StrOutputParser()
        self.verbose_printer = MyPrintHandler()
        self.agent_memory = self.init_memory()

    def init_memory(self):
        memory = ConversationTokenBufferMemory(llm=self.llm, max_token_limit=4000)
        memory.save_context({"input": "\ninit"}, {"output": "\n开始"})
        return memory

    def run(self, task_description: str) -> str:
        print("开始执行任务...")
        thought_step_count = 0

        # 初始化代理内存
        agent_memory = self.agent_memory

        while thought_step_count < self.max_thought_steps:
            print(f"思考步骤 {thought_step_count + 1}")
            action, response = self.__step(task_description, agent_memory)

            # 如果 Action 是 FINISH，则结束
            if action.name == "FINISH":
                final_chain = self.final_prompt | self.llm | StrOutputParser()
                reply = final_chain.invoke({
                    "task_description": task_description,
                    "memory": agent_memory
                })
                print(f"----\n最终回复:\n{reply}")
                return reply

            # 执行动作
            action_result = self.__exec_action(action)
            # 更新记忆
            self.update_memory(response, action_result)

            thought_step_count += 1

            if thought_step_count >= self.max_thought_steps:
                # 如果思考步数达到上限，返回错误信息
                print("任务未完成！")
                return "任务未完成！"

    def __step(self, task_description, memory) -> Tuple[ActionModel, str]:
        response = ""
        for s in self.llm_chain.stream({
            "task_description": task_description,
            "memory": memory
        }, config={"callbacks": [self.verbose_printer]}):
            response += s
        print(f"----\nResponse:\n{response}")
        action = self.output_parser.parse(response)
        return action, response

    def __exec_action(self, action: ActionModel) -> str:
        if not action or not action.name:
            print("未提供有效的动作或工具名称")
            return "未提供有效的动作或工具名称"

        tool = self.tools.get(action.name)
        if not tool:
            print(f"未找到名称为 {action.name} 的工具")
            return f"未找到名称为 {action.name} 的工具"

        try:
            return tool.run(action.args)
        except ValidationError as e:
            return f"参数校验错误: {str(e)}, 参数: {action.args}"
        except Exception as e:
            return f"执行出错: {str(e)}, 类型: {type(e).__name__}, 参数: {action.args}"

    def update_memory(self, response, observation):
        self.agent_memory.save_context(
            {"input": response},
            {"output": "\n返回结果:\n" + str(observation)}
        )
