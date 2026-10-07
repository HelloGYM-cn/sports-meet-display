from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import sys
import io
import json

app = FastAPI()

# ============ 全局状态 ============
DEFAULT_LABELS = {
    "rank":   "名次",
    "name":   "姓名",
    "team":   "单位",
    "score":  "成绩",
    "record": "破纪录",
}

state = {
    "config": {
        "meetName": "2026年春季运动会",
        "theme": "olympic",
        "screenMode": "auto",
        "rotationInterval": 8,
        "labels": dict(DEFAULT_LABELS),
    },
    "event": "等待比赛",
    "results": [],
    "nextEvent": "",
    "blackout": False,
    # 多项目缓存：{ "男子100米": [{...}, {...}], "女子跳远": [...] }
    "events": {},
    # 奖牌榜：{ "计算机学院": {"gold": 1, "silver": 2, "bronze": 0}, ... }
    "medals": {},
    # 当前展示的奖牌榜（由后端计算，前端直接读）
    "medalList": [],
}

clients: List[WebSocket] = []


async def broadcast(msg: dict):
    dead = []
    for c in clients:
        try:
            await c.send_json(msg)
        except Exception:
            dead.append(c)
    for c in dead:
        if c in clients:
            clients.remove(c)


def recompute_medals():
    """根据 state['events'] 里所有项目的成绩，重新计算奖牌榜"""
    tally: Dict[str, Dict[str, int]] = {}
    for ev_name, results in state["events"].items():
        for i, r in enumerate(results[:3]):
            team = (r.get("team") or "").strip()
            if not team:
                continue
            if team not in tally:
                tally[team] = {"gold": 0, "silver": 0, "bronze": 0}
            if i == 0:
                tally[team]["gold"] += 1
            elif i == 1:
                tally[team]["silver"] += 1
            elif i == 2:
                tally[team]["bronze"] += 1

    # 排序：金牌 > 银牌 > 铜牌 > 队名
    ranked = sorted(
        tally.items(),
        key=lambda kv: (-kv[1]["gold"], -kv[1]["silver"], -kv[1]["bronze"], kv[0])
    )
    state["medals"] = dict(tally)
    state["medalList"] = [
        {"team": t, "gold": m["gold"], "silver": m["silver"], "bronze": m["bronze"],
         "total": m["gold"] + m["silver"] + m["bronze"]}
        for t, m in ranked
    ]


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    try:
        await ws.send_json({"type": "full_state", "data": {
            "config": state["config"],
            "event": state["event"],
            "results": state["results"],
            "nextEvent": state["nextEvent"],
            "medalList": state["medalList"],
            "blackout": state["blackout"],
        }})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in clients:
            clients.remove(ws)
    except Exception as e:
        print(f"[WS] 后端异常: {e}")
        if ws in clients:
            clients.remove(ws)


# ============ 数据模型 ============
class ResultItem(BaseModel):
    name: str
    team: str = ""
    score: str = ""
    isRecord: bool = False


class ResultPayload(BaseModel):
    event: str
    results: List[ResultItem]


# ============ API ============
@app.post("/api/result")
async def update_result(payload: ResultPayload):
    # 统一格式化成绩：能转成数字的保留 2 位小数
    formatted = []
    for r in payload.results:
        score_raw = (r.score or "").strip()
        try:
            score = f"{float(score_raw):.2f}"
        except (ValueError, TypeError):
            score = score_raw
        formatted.append({
            "name": r.name,
            "team": r.team,
            "score": score,
            "isRecord": r.isRecord,
        })

    state["event"] = payload.event
    state["results"] = formatted
    state["events"][payload.event] = formatted
    recompute_medals()

    await broadcast({"type": "score_update", "data": {
        "event": state["event"],
        "results": state["results"],
        "medalList": state["medalList"],
    }})
    return {"ok": True}

@app.post("/api/next")
async def set_next(payload: dict):
    state["nextEvent"] = payload.get("nextEvent", "")
    await broadcast({"type": "next_update", "data": state["nextEvent"]})
    return {"ok": True}


@app.post("/api/config")
async def update_config(payload: dict):
    state["config"].update(payload)
    await broadcast({"type": "config_update", "data": state["config"]})
    return {"ok": True}


@app.post("/api/control/blackout")
async def blackout(on: bool = True):
    state["blackout"] = on
    await broadcast({"type": "blackout", "data": on})
    return {"ok": True}


@app.get("/api/state")
async def get_state():
    return state


@app.get("/api/config")
async def get_config():
    return state["config"]


@app.get("/api/events")
async def get_events():
    """返回所有已缓存的项目名"""
    return list(state["events"].keys())


@app.get("/api/event/{name}")
async def get_event(name: str):
    """返回某个项目的历史成绩"""
    return state["events"].get(name, [])


@app.delete("/api/event/{name}")
async def delete_event(name: str):
    """删除某个项目的缓存"""
    if name in state["events"]:
        del state["events"][name]
        recompute_medals()
        await broadcast({"type": "config_update", "data": state["config"]})
        return {"ok": True}
    return {"ok": False, "error": "not found"}


@app.post("/api/import_excel")
async def import_excel(file: UploadFile = File(...)):
    """导入 Excel，返回解析后的成绩列表"""
    try:
        import openpyxl
    except ImportError:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "缺少 openpyxl，请运行: pip install openpyxl"}
        )

    content = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return {"ok": False, "error": "文件为空"}

        # 假定第一行是表头，尝试智能识别列
        header = [str(c).strip() if c is not None else "" for c in rows[0]]

        def find_col(*keywords):
            for i, h in enumerate(header):
                for kw in keywords:
                    if kw in h:
                        return i
            return -1

        col_name  = find_col("姓名", "名字", "运动员")
        col_team  = find_col("单位", "班级", "学院", "部门", "队伍", "代表队")
        col_score = find_col("成绩", "用时", "得分", "分数", "时间")
        col_rec   = find_col("纪录", "破纪录", "备注")

        # 如果识别不到表头，就按 0/1/2 列位置猜
        if col_name < 0:
            col_name, col_team, col_score = 0, 1, 2

        results = []
        for row in rows[1:]:
            if not row or row[col_name] is None:
                continue
            name = str(row[col_name]).strip()
            if not name:
                continue
            team  = str(row[col_team]).strip()  if col_team  >= 0 and col_team  < len(row) and row[col_team]  is not None else ""
            score = str(row[col_score]).strip() if col_score >= 0 and col_score < len(row) and row[col_score] is not None else ""
            rec_raw = str(row[col_rec]).strip() if col_rec >= 0 and col_rec < len(row) and row[col_rec] is not None else ""
            is_rec = rec_raw.lower() in ("是", "y", "yes", "true", "1", "★", "破纪录", "✓", "√", "对", "有")

            results.append({
                "name": name,
                "team": team,
                "score": score,
                "isRecord": is_rec,
            })

        # 自动排序（数字成绩）
        try:
            results.sort(key=lambda r: float(r["score"]))
        except (ValueError, TypeError):
            pass

        return {"ok": True, "results": results, "count": len(results)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============ 静态资源 ============
def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")


@app.get("/screen")
async def screen_page():
    return FileResponse(resource_path("static/screen.html"))


@app.get("/ref")
async def ref_page():
    return FileResponse(resource_path("static/ref.html"))


@app.get("/")
async def index():
    return FileResponse(resource_path("static/screen.html"))
