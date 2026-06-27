import sys, re, json
from flask import Flask, request
import pymysql

app = Flask(__name__)

DB_CONFIG = {
    'host': '192.168.3.39',
    'port': 3306,
    'user': 'dify',
    'password': 'abcdef',
    'database': 'rate_db',
    'connect_timeout': 5
}

def parse_xml(xml_str):
    records = []
    blocks = re.findall(r'<data>(.*?)<endl/>', xml_str, re.DOTALL)
    for block in blocks:
        record = {}
        for field in ['Method', 'CardName', 'value', 'rate', 'Region', 'Groupname']:
            m = re.search(rf'<{field}>(.*?)</{field}>', block)
            record[field.lower()] = m.group(1) if m else ''
        if record:
            records.append(record)
    return records

@app.route('/insert', methods=['POST'])
def insert():
    data = request.get_data(as_text=True)
    if not data:
        return {"error": "no data received"}, 400
    
    try:
        obj = json.loads(data)
        if isinstance(obj, dict) and 'text' in obj:
            data = obj['text']
    except:
        pass
    
    records = parse_xml(data)
    if not records:
        return {"error": "no valid records"}, 400
    
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        insert_count, update_count = 0, 0
        
        # 插入一条数据之前会由这几步  
        # 第一步是：查询是否存在  查询标准是method（方法）, cardname（卡号）, value（面值范围）, groupname（群名）
        # 第二步是：根据是否存在判断是插入还是更新
        # 第三步是：根据插入或更新判断是否需要更新btime
        for r in records:
            cursor.execute(
                "SELECT COUNT(*) FROM t_rate WHERE method=%s AND cardname=%s AND value=%s AND groupname=%s",
                (r['method'], r['cardname'], r['value'], r['groupname'])
            )
            exists = cursor.fetchone()[0]
            
            if exists:
                cursor.execute(
                    "UPDATE t_rate SET rate=%s, btime=NOW() WHERE method=%s AND cardname=%s AND value=%s AND groupname=%s",
                    (r['rate'], r['method'], r['cardname'], r['value'], r['groupname'])
                )
                update_count += 1
            else:
                cursor.execute(
                    "INSERT INTO t_rate(method,cardname,value,rate,region,groupname) VALUES(%s,%s,%s,%s,%s,%s)",
                    (r['method'], r['cardname'], r['value'], r['rate'], r['region'], r['groupname'])
                )
                insert_count += 1
        
        conn.commit()
        return {"result": "success", "insert": insert_count, "update": update_count}
    except Exception as e:
        if conn:
            conn.rollback()
        return {"error": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

app.run(host='0.0.0.0', port=9999)
