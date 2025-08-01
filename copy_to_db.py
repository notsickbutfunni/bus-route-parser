import json
import psycopg2

conn = psycopg2.connect(
    dbname="bus_routes",
    user="postgres",
    password="root",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

with open("routes_test.json", "r", encoding="utf-8") as f:
    routes_data = json.load(f)

for route in routes_data:
    try:
        url = route.get("url")
        route_info = route.get("route_info", {})

        number = route_info.get("route_type_and_number")
        transport_type = None

        if number:
            if "Автобус" in number:
                transport_type = "Автобус"
            elif "Троллейбус" in number:
                transport_type = "Троллейбус"
            elif "Маршрутка" in number:
                transport_type = "Маршрутка"

        cursor.execute("""
            INSERT INTO routes (url, number)
            VALUES (%s, %s)
            RETURNING id
        """, (url, number))
        route_id = cursor.fetchone()[0]
        conn.commit()

        # DIRECTIONS
        directions = route.get("directions", [])
        for direction in directions:
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
                    INSERT INTO directions (route_id, stop_id, direction_order)
                    VALUES (%s, %s, %s)
                """, (route_id, stop_id, order))
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
            cursor.execute("""
                INSERT INTO schedule (route_id, day_type, validity, times)
                VALUES (%s, %s, %s, %s)
            """, (
                route_id,
                sched.get("day_type"),
                sched.get("validity"),
                times_str
            ))
        conn.commit()
    
    except Exception as e:
        print(f"Ошибка при вставке маршрута {url}: {e}")
        conn.rollback()

cursor.close()
conn.close()
