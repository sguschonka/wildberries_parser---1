import asyncio
import re
from datetime import datetime

import pandas
from playwright.async_api import async_playwright

filename = f"результаты_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"


async def parse(page, data):
    await page.wait_for_selector("div.product-card__wrapper")
    product_info = page.locator("div.product-card__wrapper")
    count = await product_info.count()
    for i in range(count):
        try:
            wrapper = product_info.nth(i)
            product_name_locator = wrapper.locator(
                "span.product-card__name"
            ).nth(0)
            product_link_locator = wrapper.locator("a.product-card__link")
            product_price_locator = wrapper.locator(
                "ins.price__lower-price"
            ).nth(0)
            product_rating_locator = wrapper.locator("span.address-rate-mini")
            product_date_locator = wrapper.locator(
                "a.product-card__add-basket > span.btn-text"
            )

            (
                product_rating,
                product_date,
                product_price_row,
                product_link,
                product_name,
            ) = await asyncio.gather(
                product_rating_locator.inner_text(),
                product_date_locator.inner_text(),
                product_price_locator.text_content(),
                product_link_locator.get_attribute("href"),
                product_name_locator.inner_text(),
            )

            product_price = re.sub(
                r"[\u202f\xa0]", "", product_price_row
            ).strip()

            if "/" in product_name:
                product_name = product_name.replace("/", "", 1).strip()

            if "" == product_rating:
                product_rating = "Нет оценок"

            # выбираем только то, что действительно относится к искомому
            if (
                "Лабубу" in product_name
                or "Labubu" in product_name
                or "LABUBU" in product_name
                or "ЛАБУБУ" in product_name
                or "лабубу" in product_name
                or "labubu" in product_name
            ):
                data.append(
                    {
                        "Название карточки": product_name,
                        "Ссылка": product_link,
                        "Цена": product_price,
                        "Рейтинг": product_rating,
                        "Дата доставки": product_date,
                    }
                )
        except Exception as e:
            print(f"Ошибка при обработке {i} лабубу: {e}")


async def main():
    data = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        # создаем контекст чтобы симулировать дея-сть пользователя (anti-bot)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1024},
            java_script_enabled=True,
        )

        page = await context.new_page()
        await page.goto(
            "https://www.wildberries.ru/catalog/0/search.aspx?search=%D0%BB%D0%B0%D0%B1%D1%83%D0%B1%D1%83+%D0%B1%D1%80%D0%B5%D0%BB%D0%BE%D0%BA&targeturl=ST&xsearch=true"
        )

        # wb создает страницы бесконечно. дальше - проверка добавляются ли карточки нужного нам товара или нет, если нет - мы на последней возможной странице
        prev_len = 0
        while True:
            await auto_scroll(page)
            await parse(page, data)
            if len(data) == prev_len:
                print("Новые карточки не появились — стоп")
                break
            prev_len = len(data)
            await asyncio.sleep(1)
            if not await goto_next(page):
                break

    await browser.close()
    await file_update(data)


async def auto_scroll(page, scroll_times=5, pause=0.2):
    await page.wait_for_selector("div.product-card__wrapper")
    for _ in range(scroll_times):
        await page.mouse.wheel(0, 1700)
        await asyncio.sleep(pause)


async def goto_next(browser_page):
    # Все переходные кнопки (a)
    buttons = browser_page.locator("a.pagination__item.pagination-item")

    if await buttons.count() == 0:
        print("Кнопки пагинации не найдены")
        return False

    # Активная страница (span)
    active = browser_page.locator("span.pagination__item.active")
    if await active.count() == 0:
        print("Активная страница (span.active) не найдена")
        return False

    active_text = await active.text_content()
    print(f"Активная страница: {active_text}")

    # Переход на следующую
    next_btn = None
    for i in range(await buttons.count()):
        text = await buttons.nth(i).text_content()
        if text == str(int(active_text) + 1):  # ищем следующую
            next_btn = buttons.nth(i)
            break

    if next_btn:
        print(f"Переход на страницу: {int(active_text) + 1}")
        await next_btn.click()
        await browser_page.wait_for_selector("div.product-card__wrapper")
        await asyncio.sleep(0.5)
        return True
    else:
        print("Последняя страница достигнута")
        return False


async def file_update(data):
    product_without_rating = sum(
        1 for value in data if value["Рейтинг"] == "Нет оценок"
    )
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now()}] Собрано: {len(data)}, из них без рейтинга: {product_without_rating}"
        )
    datafile = pandas.DataFrame(data)
    with pandas.ExcelWriter(filename, engine="openpyxl") as writer:
        datafile.to_excel(
            writer,
            sheet_name="Сбор данных о брелках лабубу на Wildberries",
            index=False,
        )


if __name__ == "__main__":
    asyncio.run(main())
