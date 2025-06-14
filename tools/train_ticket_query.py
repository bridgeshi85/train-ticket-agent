from typing import List
from langchain_core.tools import StructuredTool
import asyncio
from utils.ticket_query_scraper import extract_train_data_with_browser  # 改造你的 Playwright 脚本成一个可复用函数


def search_train_ticket(
        origin: str,
        destination: str,
        date: str,
        departure_time_start: str = "00:00",
        departure_time_end: str = "23:59"
) -> List[dict]:
    """按条件查询火车票"""

    async def _run():
        return await extract_train_data_with_browser(origin, destination, date)

    # 用 asyncio 运行异步逻辑
    result = asyncio.run(_run())
    return result


search_train_ticket_tool = StructuredTool.from_function(
    func=search_train_ticket,
    name="查询火车票",
    description="调用12306官网，真实查询火车票"
)
