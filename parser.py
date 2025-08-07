from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json, time

BASE_URL = "https://wikiroutes.info"
CATALOG_URL = BASE_URL + "/almaty/catalog"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0"}

def get_route_links_with_selenium(driver):
    driver.get(CATALOG_URL)
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
    )
    soup = BeautifulSoup(driver.page_source, "html.parser")
    links = []

    for a in soup.select("a[href^='/almaty?routes=']"):
        full_url = BASE_URL + a['href']
        links.append(full_url)

    return list(set(links))

def get_route_info(soup):
    route_info = {}

    try:
        type_number_div = soup.find("div", class_="uPKuXzftArnc")
        if type_number_div:
            type_number = type_number_div.find("div", class_="TSkRYMTgNY uaYqWMCtQlV")
            if type_number:
                route_info["route_type_and_number"] = type_number.get_text(strip=True).replace('\xa0','')

        fare_div = soup.find("div", class_="EqasqKWRMftkOa")
        if fare_div:
            fare = fare_div.find("div", class_="gwt-HTML YrjBWjbVyqdT")
            if fare:
                route_info["fare"] = fare.get_text(strip=True).replace('\xa0', '')

        company_div = soup.find("div", class_="hyZIaTmwOcIMZD")
        if company_div:
            company = company_div.find("div", class_="gwt-HTML mkOptJDbOyM")
            if company:
                route_info["operator"] = company.get_text(strip=True)

        path_div = soup.find("div", class_="lzuCoYCH")
        if path_div:
            path = path_div.find("div", class_="gwt-HTML ZheJfolqdgvvrW")
            if path:
                route_info["path"] = path.get_text(strip=True)

        tech_div = soup.find("div", class_="GoMyLSjuUJOgjv")
        if tech_div:
            tech_texts = tech_div.find_all("div", class_="bhyEwVEQx")
            tech_info = []
            for item in tech_texts:
                tech_info.append(item.get_text(separator=" ", strip=True))
            route_info["technical_info"] = "\n".join(tech_info)

        add_div = soup.find("div", class_="XceUvFYOS")
        if add_div:
            add_info = add_div.find("div", class_="gwt-HTML DSzMiMUKgUtpRr")
            if add_info:
                route_info["additional_info"] = add_info.get_text(strip=True)

        edited_div = soup.find("div", class_="UFnLSfWcPZCY last-edited")
        if edited_div:
            last_edit = edited_div.find("div", class_="gwt-HTML ISnKzuDIO")
            if last_edit:
                route_info["last_edited"] = last_edit.get_text(strip=True)

    except Exception as e:
        print("Ошибка при парсинге route_info:", e)

    return route_info



def get_directions(soup):
    directions =[]
    stops_blocks = soup.select(".stops-list-items-container")

    for block in stops_blocks:
        stops = [stop.get_text(strip=True) for stop in block.select(".stops-list-item")]
        if stops:
            directions.append(stops)

    return directions if directions else None


def get_comments(soup):
    comments = []
    for c in soup.select(".comment"):
        user = c.select_one(".comment-user-name")
        text = c.select_one(".comment-text-content")
        date = c.select_one(".comment-date")
        comments.append({
            "username": user.get_text(strip=True) if user else None,
            "comment_text": text.get_text(strip=True) if text else None,
            "date_time": date.get_text(strip=True) if date else None,
        })
        
    return comments

def get_schedule(soup):
    schedule_data = []
    blocks = soup.find_all("div", class_="xrrCPhRNd")
    
    for block in blocks:
        titles = block.find_all("div", class_="uuqwkRKOGbztN")
        contents = block.find_all("div", class_="DHIMIHTIdgrB")
        
        
        if len(titles) >= 2 and len(contents) >= 2:
            day_type_and_validity = contents[0].get_text(separator=" ", strip=True)
            
            parts = day_type_and_validity.split()
            if len(parts) >= 2:
                day_type = parts[0] + " " + parts[1] if parts[0] == "по" else parts[0]
                validity = " ".join(parts[2:]) if len(parts) > 2 else ""
            else:
                day_type = day_type_and_validity
                validity = ""
            
            times_raw = contents[1].get_text(separator=" ", strip=True)
            times = [t.strip() for t in times_raw.split(",") if t.strip()]
            
            schedule_data.append({
                "day_type": day_type,
                "validity": validity,
                "times": times
            })
    
    return schedule_data

def get_coordinates(driver):
    script = """
    let allCoords = [];
    for (let k in window) {
        try {
            let obj = window[k];
            if (obj && typeof obj === 'object' && obj._layers) {
                for (let id in obj._layers) {
                    let layer = obj._layers[id];
                    if (layer && layer._latlngs) {
                        if (Array.isArray(layer._latlngs[0])) {
                            for (let group of layer._latlngs) {
                                for (let point of group) {
                                    allCoords.push([point.lat, point.lng]);
                                }
                            }
                        } else {
                            for (let point of layer._latlngs) {
                                allCoords.push([point.lat, point.lng]);
                            }
                        }
                    }
                }
            }
        } catch (e) {}
    }
    return allCoords;
    """
    return driver.execute_script(script)



def parse_route_page(driver, url):
    driver.get(url)

    try:
        WebDriverWait(driver, 12).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "stops-list-items-container"))
        )
    except:
        pass

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1.5)

    try:
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.ID, "uzTKaRTbLuti"))
        )
    except:
        pass

    soup = BeautifulSoup(driver.page_source, "html.parser")

    route_info = get_route_info(soup)
    directions = get_directions(soup)
    comments = get_comments(soup)
    schedule = get_schedule(soup)
    raw_coordinates = get_coordinates(driver)
    coordinates = [
        {"lat": lat, "lon": lon}
        for (lat, lon) in enumerate(raw_coordinates)
    ]

    return {
        "url": url,
        "route_info": route_info,
        "directions": directions,
        "comments": comments,
        "schedule": schedule,
        "coordinates": coordinates
    }


def main(driver):
    links = get_route_links_with_selenium(driver)
    print(f"Найдено маршрутов: {len(links)}")

    MAX_ROUTES = 405
    data = []

    for i, link in enumerate(links[:MAX_ROUTES], start=1):
        print(f"[{i}/{min(MAX_ROUTES, len(links))}] {link}")
        try:
            route_data = parse_route_page(driver, link)
            data.append(route_data)
            time.sleep(1)
        except Exception as e:
            print(f"Ошибка на {link}: {e}")

    with open("routes_test.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    driver = webdriver.Chrome()
    try:
        main(driver)
    finally:
        driver.quit()
