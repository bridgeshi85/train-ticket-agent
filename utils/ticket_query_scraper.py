import asyncio
from typing import List

from playwright.async_api import async_playwright
from pypinyin import lazy_pinyin, Style


async def select_city(page, selector: str, city_name: str):
    initials = get_pinyin(city_name)
    await page.click(selector)
    for c in initials:
        await page.keyboard.press(c)
        await page.wait_for_timeout(100)
    await page.wait_for_timeout(500)
    await page.keyboard.press("Enter")


async def extract_train_data(page):
    rows = await page.query_selector_all("#queryLeftTable tr.bgc")
    results = []

    for row in rows[:10]:  # 只取前10条
        train_info = {}

        # 车次编号
        train_number_el = await row.query_selector("div.train a.number")
        train_info["train_number"] = (await train_number_el.text_content()).strip() if train_number_el else "-"

        # 出发地与到达地
        station_els = await row.query_selector_all("div.cdz strong")
        from_station_el = station_els[0] if len(station_els) > 0 else None
        to_station_el = station_els[1] if len(station_els) > 1 else None
        train_info["origin"] = (await from_station_el.text_content()).strip() if from_station_el else "-"
        train_info["destination"] = (await to_station_el.text_content()).strip() if to_station_el else "-"

        # 出发时间与到达时间
        departure_time_el = await row.query_selector("div.cds .start-t")
        arrival_time_el = await row.query_selector("div.cds .color999")
        train_info["departure_time"] = (await departure_time_el.text_content()).strip() if departure_time_el else "-"
        train_info["arrival_time"] = (await arrival_time_el.text_content()).strip() if arrival_time_el else "-"

        # 历时
        duration_el = await row.query_selector("div.ls strong")
        train_info["duration"] = (await duration_el.text_content()).strip() if duration_el else "-"

        # 各座位类型
        seat_cells = await row.query_selector_all("td")
        try:
            train_info["business_seat"] = (await seat_cells[1].inner_text()).strip()
            train_info["first_class_seat"] = (await seat_cells[3].inner_text()).strip()
            train_info["second_class_seat"] = (await seat_cells[4].inner_text()).strip()
        except IndexError:
            train_info["business_seat"] = "-"
            train_info["first_class_seat"] = "-"
            train_info["second_class_seat"] = "-"

        results.append(train_info)

    return results


def get_pinyin(text: str) -> str:
    """
    将中文字符串转换为拼音首字母，例如“上海” -> "sh"
    """
    return ''.join(lazy_pinyin(text, style=Style.NORMAL))


async def extract_train_data_with_browser(origin: str, destination: str, date: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 设置为 True 可无头运行
        context = await browser.new_context()
        page = await context.new_page()

        # 打开 12306 首页
        await page.goto("https://www.12306.cn/index/")

        await select_city(page, "#fromStationText", origin)
        await select_city(page, "#toStationText", destination)

        # 填写出发日期（注意：必须是未来的日期，格式：YYYY-MM-DD）
        await page.fill('#train_date', date)

        # 等待新页面打开
        async with context.expect_page() as new_page_info:
            await page.click('#search_one')
        result_page = await new_page_info.value  # 获取新打开的 tab

        await result_page.wait_for_load_state('domcontentloaded')
        await result_page.wait_for_selector("#queryLeftTable", timeout=10000)
        result = await extract_train_data(result_page)
        print("查询结果：")
        for train in result:
            print(train)
        print("查询完成")
        await browser.close()
        return {
            "message": "查询成功",
            "results": result
        }
