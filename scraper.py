from playwright.sync_api import sync_playwright
import time
import random
import re
from datetime import datetime
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import os
import json

# 국가 리스트 (이 부분은 필요에 맞게 수정하세요)
country_settings = [
    {"country": "United States"},
    {"country": "South Korea"},
    {"country": "Hungary"},
    {"country": "Iceland"},
    {"country": "India"},
    {"country": "Ireland"},
    {"country": "Isle of Man"},
    {"country": "Israel"},
    {"country": "Azerbaijan"},
    {"country": "Bahamas"},
    {"country": "Bahrain"},
    {"country": "Bangladesh"},
    {"country": "Barbados"},
    {"country": "Belgium"},
    {"country": "Benin"},
    {"country": "Bhutan"},
    {"country": "Japan"},
    {"country": "Algeria"},
    {"country": "Andorra"},
    {"country": "Angola"},
    {"country": "Argentina"},
    {"country": "Armenia"},
    {"country": "Aruba"},
    {"country": "Australia"},
    {"country": "Austria"},
    {"country": "Bolivia"},
    {"country": "Bosnia and Herzegovina"},
    {"country": "Brazil"},
    {"country": "Brunei Darussalam"},
    {"country": "Bulgaria"},
    {"country": "Burkina Faso"},
    {"country": "Burundi"},
    {"country": "Cambodia"},
    {"country": "Cameroon"},
    {"country": "Canada"},
    {"country": "Cape Verde"},
    {"country": "Central African Republic"},
    {"country": "Chad"},
    {"country": "Chile"},
    {"country": "Colombia"},
    {"country": "Congo"},
    {"country": "Costa Rica"},
    {"country": "Cote D'ivoire"},
    {"country": "Croatia"},
    {"country": "Cyprus"},
    {"country": "Czech Republic"},
    {"country": "Denmark"},
    {"country": "Dominican Republic"},
    {"country": "East Timor"},
    {"country": "Ecuador"},
    {"country": "Egypt"},
    {"country": "El Salvador"},
    {"country": "Eritrea"},
    {"country": "Estonia"},
    {"country": "Falkland Islands (Malvinas)"},
    {"country": "Finland"},
    {"country": "France"},
    {"country": "Gabon"},
    {"country": "Gambia"},
    {"country": "Georgia"},
    {"country": "Germany"},
    {"country": "Ghana"},
    {"country": "Gibraltar"},
    {"country": "Greece"},
    {"country": "Guadeloupe"},
    {"country": "Guatemala"},
    {"country": "Guernsey"},
    {"country": "Guinea"},
    {"country": "Guinea-Bissau"},
    {"country": "Haiti"},
    {"country": "Holy See (Vatican City State)"},
    {"country": "Honduras"},
    {"country": "Hong Kong"},
    {"country": "Hungary"},
    {"country": "Iceland"},
    {"country": "India"},
    {"country": "Ireland"},
    {"country": "Isle of Man"},
    {"country": "Israel"},
    {"country": "Italy"},
    {"country": "Jamaica"},
    {"country": "Japan"},
    {"country": "Jersey"},
    {"country": "Jordan"},
    {"country": "Kazakhstan"},
    {"country": "Kenya"},
    {"country": "Kuwait"},
    {"country": "Kyrgyzstan"},
    {"country": "Lao People's Democratic Republic"},
    {"country": "Latvia"},
    {"country": "Liechtenstein"},
    {"country": "Lithuania"},
    {"country": "Luxembourg"},
    {"country": "Macau"},
    {"country": "Madagascar"},
    {"country": "Malaysia"},
    {"country": "Maldives"},
    {"country": "Mali"},
    {"country": "Malta"},
    {"country": "Martinique"},
    {"country": "Mauritania"},
    {"country": "Mauritius"},
    {"country": "Mayotte"},
    {"country": "Mexico"},
    {"country": "Mongolia"},
    {"country": "Montenegro"},
    {"country": "Morocco"},
    {"country": "Mozambique"},
    {"country": "Myanmar"},
    {"country": "Nepal"},
    {"country": "Netherlands"},
    {"country": "New Zealand"},
    {"country": "Nicaragua"},
    {"country": "Norway"},
    {"country": "Oman"},
    {"country": "Palestine"},
    {"country": "Panama"},
    {"country": "Paraguay"},
    {"country": "Peru"},
    {"country": "Philippines"},
    {"country": "Poland"},
    {"country": "Portugal"},
    {"country": "Qatar"},
    {"country": "Republic of Moldova"},
    {"country": "Republic of North Macedonia"},
    {"country": "Reunion"},
    {"country": "Romania"},
    {"country": "Rwanda"},
    {"country": "San Marino"},
    {"country": "Sao Tome And Principe"},
    {"country": "Saudi Arabia"},
    {"country": "Senegal"},
    {"country": "Serbia"},
    {"country": "Singapore"},
    {"country": "Slovakia"},
    {"country": "Slovenia"},
    {"country": "South Africa"},
    {"country": "South Korea"},
    {"country": "Spain"},
    {"country": "St. Helena"},
    {"country": "Sweden"},
    {"country": "Switzerland"},
    {"country": "Taiwan"},
    {"country": "Tanzania, United Republic of"},
    {"country": "Thailand"},
    {"country": "Trinidad and Tobago"},
    {"country": "Turkey"},
    {"country": "Tuvalu"},
    {"country": "Uganda"},
    {"country": "Ukraine"},
    {"country": "United Arab Emirates"},
    {"country": "United Kingdom"},
    {"country": "United States"},
    {"country": "Uruguay"},
    {"country": "Uzbekistan"},
    {"country": "Vanuatu"},
    {"country": "Venezuela"},
    {"country": "Vietnam"},
    {"country": "Zambia"}
]

# --- 중복 국가 제거 로직 ---
seen_countries = set()
unique_country_settings = []
for setting in country_settings:
    country_name = setting['country']
    if country_name not in seen_countries:
        unique_country_settings.append(setting)
        seen_countries.add(country_name)
print(f"중복을 제외한 총 {len(unique_country_settings)}개 국가를 처리합니다.")

# --- 가격 분리 및 브라우저 제어 함수들 (수정 없이 그대로 사용) ---
def parse_price(price_text):
    match = re.search(r'[\d,.]+', price_text)
    if not match: return "N/A", "Price Not Found"
    price_str = match.group(0)
    currency_str = price_text.replace(price_str, '').strip()
    try:
        price_value = float(price_str.replace(',', ''))
        return currency_str, price_value
    except ValueError:
        return currency_str, "Conversion Error"

def human_delay(min_seconds=1.0, max_seconds=2.5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def set_shipping_country_only(page, country):
    print(f"🌍 국가 변경 중: {country}")
    page.locator("img.header_flagIcon__5ACs6").locator("..").click()
    page.wait_for_selector("text=Shipping Preferences")
    input_box = page.get_by_label("Shipping Destination")
    input_box.fill(country)
    page.wait_for_timeout(500)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.locator("div.MuiDialogActions-root button:has-text('Save')").click()
    human_delay()
    page.wait_for_timeout(3000)

# --- 메인 로직 ---
def track_prices():
    url = "https://www.yesstyle.com/en/seapuri-scalpy-hair-serum-20ml/info.html/pid.1134798547"
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        for setting in unique_country_settings:
            page = context.new_page()
            try:
                print(f"\n▶️ {setting['country']} 처리 시작...")
                page.goto(url, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                human_delay()
                set_shipping_country_only(page, setting["country"])
                page.wait_for_selector("div[class*='priceContainer'] span[class*='sellingPrice']", timeout=10000)
                price_text = page.locator("div[class*='priceContainer'] span[class*='sellingPrice']").first.inner_text()
                currency, price = parse_price(price_text)
                print(f"✅ 가격 확인: {currency} {price}")
                results.append({"Country": setting["country"], "Currency": currency, "Price": price})
            except Exception as e:
                print(f"❌ 에러 발생: {setting['country']} / {e}")
                results.append({"Country": setting["country"], "Currency": "N/A", "Price": "Error"})
            finally:
                page.close()
        browser.close()
    
    # --- 구글 스프레드시트 저장 로직 ---
    print("\n🔄 구글 스프레드시트에 연결하여 결과 저장 중...")
    try:
        creds_json_str = os.environ.get('GOOGLE_CREDENTIALS')
        if not creds_json_str: raise ValueError("GOOGLE_CREDENTIALS Secret을 찾을 수 없습니다.")
        creds_dict = json.loads(creds_json_str)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("YesStyle 가격 추적") # 👈 본인의 구글 시트 제목
        worksheet = sh.get_worksheet(0)
        df = pd.DataFrame(results)
        worksheet.clear()
        set_with_dataframe(worksheet, df)
        print("🎉 구글 스프레드시트 업데이트 완료!")
    except Exception as e:
        print(f"🔥 구글 스프레드시트 업데이트 실패: {e}")

if __name__ == "__main__":
    track_prices()