from langchain_core.tools import StructuredTool


def finish_placeholder():
    """用于表示任务完成的占位符工具"""
    return None


finish_tool = StructuredTool.from_function(
    func=finish_placeholder,
    name="FINISH",
    description="表示任务完成"
)
