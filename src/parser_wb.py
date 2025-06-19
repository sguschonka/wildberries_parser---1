import asyncio
import re

from playwright.async_api import async_playwright


async def parse(page, data):
    await page.wait_for_selector('[class="product-card__wrapper"]')
    product_info = page.locator('[class="product-card__wrapper"]')
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

            product_price_row = await product_price_locator.text_content()
            product_price = re.sub(
                r"[\u202f\xa0]", "", product_price_row
            ).strip()
            product_link = await product_link_locator.get_attribute("href")
            product_name = await product_name_locator.inner_text()

            if "/" in product_name:
                product_name = product_name.replace("/", "", 1).strip()

            data.append(
                {
                    "Название карточки": product_name,
                    "Ссылка": product_link,
                    "Цена": product_price,
                }
            )
        except Exception as e:
            print(f"Ошибка при обработке {i} лабубу: {e}")


async def main():
    data = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # создаем контекст чтобы симулировать дея-сть пользователя (anti-bot)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        await page.goto(
            "https://www.wildberries.ru/catalog/0/search.aspx?search=%D0%BB%D0%B0%D0%B1%D1%83%D0%B1%D1%83"
        )
        while True:
            await parse(page, data)
            break

    await browser.close()
    print(data)


if __name__ == "__main__":
    asyncio.run(main())
