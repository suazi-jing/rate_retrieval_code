import sys, json
from flask import Flask, request
import pymysql

app = Flask(__name__)

@app.route('/delete', methods=['POST'])
def delete():
    data = request.get_json(force=True, silent=True) or {}
    groupname = data.get('groupname', '')
    cardnames = data.get('cardnames', [])
    cardname = data.get('cardname', '')
    delete_old = data.get('delete_old', False)
    delete_all = data.get('delete_all', False)
    
    conn = pymysql.connect(host='192.168.3.39', port=3306, user='dify', password='abcdef', database='rate_db')
    cursor = conn.cursor()
    total = 0
    msg = ""
    
    # 删除全部数据
    if delete_all:
        cursor.execute("DELETE FROM t_rate")
        total = cursor.rowcount
        msg = "删除了全部数据"
    # 删除一天前的数据
    elif delete_old:
        cursor.execute("DELETE FROM t_rate WHERE btime < DATE_SUB(NOW(), INTERVAL 1 DAY)")
        total = cursor.rowcount
        msg = "删除了一天前的全部数据"
    elif groupname:
        if cardname and not cardnames:
            cardnames = [cardname]
        
        if cardnames:
            for cn in cardnames:
                cursor.execute("DELETE FROM t_rate WHERE cardname=%s AND groupname=%s", (cn, groupname))
                total += cursor.rowcount
            msg = f"删除了群'{groupname}'中{cardnames}的数据"
        else:
            cursor.execute("DELETE FROM t_rate WHERE groupname=%s", (groupname,))
            total = cursor.rowcount
            msg = f"删除了群'{groupname}'的全部数据"
    else:
        return {"error": "groupname, delete_old or delete_all is required"}, 400
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"{msg}，共 {total} 条", file=sys.stderr)
    return {"result": "success", "deleted": total, "message": msg}

app.run(host='0.0.0.0', port=9998)

