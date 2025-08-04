import json
import psycopg2
import re

conn = psycopg2.connect(
    dbname="bus_routes",
    user="your_username",
    password="your_passwd",
    host="your_host",
    port="your_port"
)
cursor = conn.cursor()

with open("your_json.json", "r", encoding="utf-8") as f:
    routes_data = json.load(f)


def split_technical_info(text):
    if not text:
        return None, None
    pattern = r"Длина траектории рейса №1: ([\d.]+)км Остановок: (\d+)"
    match = re.search(pattern, text)
    if match:
        length = float(match.group(1))
        stops = int(match.group(2))
        return length, stops
    return None, None

def extract_bus_type(bus_number):
    if not bus_number:
        return None
    return bus_number.split()[0].strip()

def get_or_create(cursor, table, value):
    cursor.execute(f"SELECT id FROM {table} WHERE name = %s;", (value,))
    res = cursor.fetchone()
    if res:
        return res[0]
    else:
        cursor.execute(f"INSERT INTO {table} (name) VALUES (%s) RETURNING id;", (value,))
        return cursor.fetchone()[0]


for route in routes_data:
    try:
        url = route.get("url")
        route_info = route.get("route_info", {})
        
        number = route_info.get('route_type_and_number')
        fare = route_info.get("fare")
        operator = route_info.get("operator")
        path = route_info.get("path")
        technical_info = route_info.get("technical_info")
        additional_info = route_info.get("additional_info")
        length_km,stop_num = split_technical_info(technical_info)
        bus_type = extract_bus_type(number)
        bus_type_id = get_or_create(cursor, "transport_types", bus_type) if bus_type else None
        

        cursor.execute("""
            INSERT INTO routes (
                url, bus_number, fare, operator, path, 
                additional_info, bus_type,
                length_km, stop_num, bus_type_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            url, number, fare, operator, path,
            additional_info, bus_type,
            length_km, stop_num, bus_type_id
        ))
        route_id = cursor.fetchone()[0]
        conn.commit()


        # DIRECTIONS
        directions = route.get("directions", [])
        for dir_index, direction in enumerate(directions):
            direction_value = dir_index + 1  
            for order, stop_name in enumerate(direction, start=1):
                cursor.execute("SELECT id FROM stops WHERE name = %s;", (stop_name,))
                res = cursor.fetchone()
                if res:
                    stop_id = res[0]
                else:
                    cursor.execute("INSERT INTO stops (name) VALUES (%s) RETURNING id;", (stop_name,))
                    stop_id = cursor.fetchone()[0]
                    conn.commit()

                cursor.execute("""
                    INSERT INTO directions (route_id, stop_id, direction_order, direction)
                    VALUES (%s, %s, %s, %s)
                """, (route_id, stop_id, order, direction_value))
        conn.commit()

        # COMMENTS
        comments = route.get("comments", [])
        for comment in comments:
            cursor.execute("""
                INSERT INTO comments (route_id, username, comment_text, date_time)
                VALUES (%s, %s, %s, %s)
            """, (
                route_id,
                comment.get("username"),
                comment.get("comment_text"),
                comment.get("date_time"),
            ))
        conn.commit()

        # SCHEDULES
        schedule = route.get("schedule", [])
        for sched in schedule:
            times_str = ", ".join(sched.get("times", []))
            day_type = sched.get("day_type")
            validity = sched.get("validity")
            day_type_id = get_or_create(cursor, "day_types", day_type) if day_type else None
            validity_id = get_or_create(cursor, "validity_periods", validity) if validity else None

            cursor.execute("""
                INSERT INTO schedule (route_id, day_type_id, validity_id, times)
                VALUES (%s, %s, %s, %s)
            """, (
                route_id,
                day_type_id,
                validity_id,
                times_str
            ))
        
        # coordinates
        

        
    except Exception as e:
        print(f"Ошибка при вставке маршрута {url}: {e}")
        conn.rollback()

cursor.close()
conn.close()
