import os
import csv
import json
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq


# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

DATA_DIR = Path("data")
SALES_FILE = DATA_DIR / "sales.csv"
SCHEDULE_FILE = DATA_DIR / "graduation_schedule.csv"
TODO_FILE = DATA_DIR / "todos.csv"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set.")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

app = FastAPI(
    title="Coffee Shop AI Manager"
)

active_connections = []


# ==========================================
# DATA FUNCTIONS
# ==========================================

def read_csv(file_path):

    if not file_path.exists():
        return []

    with open(
        file_path,
        newline="",
        encoding="utf-8"
    ) as file:

        return list(csv.DictReader(file))


def coffee_shop_analysis():

    sales = read_csv(SALES_FILE)
    schedule = read_csv(SCHEDULE_FILE)

    if not sales:
        return {
            "error": "Sales data not found."
        }

    analyzed_rows = []

    for row in sales:

        try:

            cold_brew = int(row.get("Cold_Brew", 0))
            espresso = int(row.get("Extra_Espresso", 0))
            alt_milk = int(row.get("Alt_Milk_Oz", 0))
            wait_time = int(row.get("Wait_Time_Minutes", 0))
            cashiers = int(row.get("Cashiers_Working", 0))

            score = (
                cold_brew
                + espresso
                + alt_milk
                + wait_time * 10
            )

            analyzed_rows.append({
                "day": row.get("Day"),
                "time": row.get("Time"),
                "cold_brew": cold_brew,
                "extra_espresso": espresso,
                "alt_milk": alt_milk,
                "wait_time": wait_time,
                "cashiers": cashiers,
                "score": score
            })

        except Exception:
            continue

    busiest = sorted(
        analyzed_rows,
        key=lambda x: x["score"],
        reverse=True
    )[:5]

    return {
        "sales_records": len(sales),
        "graduation_events": schedule,
        "busiest_periods": busiest
    }


def get_agent_context():

    analysis = coffee_shop_analysis()

    return f"""
You are the Coffee Shop Manager AI.

You are helping a coffee shop prepare for a university
graduation weekend.

Historical POS analysis:

{json.dumps(analysis, indent=2)}

Your responsibilities:

1. Analyze the busiest periods.

2. Identify staffing bottlenecks.

3. If wait time is above 10 minutes:
   - If fewer than 2 cashiers are working,
     recommend another cashier.
   - If there are 2 cashiers but Cold Brew,
     Extra Espresso, or alternative milk demand is high,
     recommend a Support Barista.

4. Identify inventory preparation needs.

5. Connect busy periods with graduation events when possible.

6. Present only 2 or 3 important discoveries.

7. Give recommendations in this format:

## Key Data Discoveries

- discovery

## Staffing Recommendations

1. recommendation

## Inventory Recommendations

1. recommendation

## Suggested TODO Tasks

- task

8. Before creating TODO tasks, always ask:

"Would you like me to add these tasks to your
TODO-2026 TODO list?"

9. Only create tasks if the user explicitly says yes,
approve, or confirms.

Be helpful, professional, and concise.
"""


# ==========================================
# TODO FUNCTIONS
# ==========================================

def save_todo(task, category, ceremony="General"):

    DATA_DIR.mkdir(exist_ok=True)

    file_exists = TODO_FILE.exists()

    with open(
        TODO_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        if not file_exists:

            writer.writerow([
                "Task",
                "Category",
                "Ceremony",
                "Date_Added"
            ])

        writer.writerow([
            task,
            category,
            ceremony,
            datetime.now().strftime("%Y-%m-%d")
        ])


# ==========================================
# GROQ AI
# ==========================================

def ask_groq(user_message):

    if not client:

        return (
            "Groq API key is not configured yet. "
            "Please add GROQ_API_KEY."
        )

    completion = client.chat.completions.create(

        model="llama-3.3-70b-versatile",

        messages=[

            {
                "role": "system",
                "content": get_agent_context()
            },

            {
                "role": "user",
                "content": user_message
            }

        ],

        temperature=0.4,

        max_tokens=1200

    )

    return completion.choices[0].message.content


# ==========================================
# WEBSOCKET
# ==========================================

@app.websocket("/ws")

async def websocket_endpoint(
    websocket: WebSocket
):

    await websocket.accept()

    active_connections.append(websocket)

    await websocket.send_text(
        "☕ Coffee Shop AI Manager connected!"
    )

    try:

        while True:

            user_message = await websocket.receive_text()

            await websocket.send_text(
                "_Analyzing coffee shop data..._"
            )

            response = ask_groq(
                user_message
            )

            await websocket.send_text(
                response
            )

    except WebSocketDisconnect:

        if websocket in active_connections:

            active_connections.remove(
                websocket
            )


# ==========================================
# HTTP CHAT
# ==========================================

class UserPrompt(BaseModel):

    prompt: str


@app.post("/chat")

def chat_with_agent(
    payload: UserPrompt
):

    try:

        response = ask_groq(
            payload.prompt
        )

        return {

            "status": "success",

            "response": response

        }

    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=str(error)

        )


# ==========================================
# TODO API
# ==========================================

class TodoRequest(BaseModel):

    task: str
    category: str
    ceremony: str = "General"


@app.post("/todo")

def create_todo(
    payload: TodoRequest
):

    save_todo(

        payload.task,

        payload.category,

        payload.ceremony

    )

    return {

        "status": "success",

        "message":
        "Task added to TODO-2026."

    }


# ==========================================
# WEB INTERFACE
# ==========================================

@app.get(
    "/",
    response_class=HTMLResponse
)

async def get_chat_ui():

    return """

<!DOCTYPE html>

<html>

<head>

<title>Coffee Shop AI Manager</title>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<style>

body {
    display: flex;
    height: 100vh;
    margin: 0;
    font-family: Arial, sans-serif;
}

#sidebar {
    width: 250px;
    background: #3E2723;
    color: white;
    padding: 20px;
}

#main {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    background: #FAF8F6;
}

#chat-history {
    flex-grow: 1;
    padding: 20px;
    overflow-y: auto;
    background: #F5EFEB;
}

#input-area {
    padding: 20px;
    display: flex;
    background: white;
}

input {
    flex-grow: 1;
    padding: 14px;
    border-radius: 8px;
    border: 1px solid #D7CCC8;
    margin-right: 10px;
}

button {
    padding: 12px 25px;
    background: #6D4C41;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
}

.message {
    margin-bottom: 15px;
    padding: 14px;
    border-radius: 10px;
    max-width: 85%;
}

.user-msg {
    background: #EFEBE9;
    margin-left: auto;
}

.agent-msg {
    background: white;
}

</style>

</head>

<body>

<div id="sidebar">

<h2>☕ Coffee Shop Manager</h2>

<p>AI Business Analyst</p>

<p>📊 Sales Analysis</p>

<p>👥 Staffing</p>

<p>📦 Inventory</p>

<p>🎓 Graduation Planning</p>

<p>📋 TODO Management</p>

</div>


<div id="main">

<div id="chat-history"></div>


<div id="input-area">

<input
type="text"
id="msg"
placeholder="Ask Coffee Shop Manager..."
onkeypress="
if(event.key === 'Enter')
sendMessage()
">

<button
onclick="sendMessage()"
>

Send

</button>

</div>

</div>


<script>

const protocol =
window.location.protocol === 'https:'
? 'wss:'
: 'ws:';


const ws =
new WebSocket(
`${protocol}//${window.location.host}/ws`
);


const history =
document.getElementById(
'chat-history'
);


ws.onmessage =
function(event) {

const parsedHtml =
marked.parse(
event.data
);


history.innerHTML +=

`

<div class="message agent-msg">

<b>☕ Coffee Shop AI</b>

<div>

${parsedHtml}

</div>

</div>

`;


history.scrollTop =
history.scrollHeight;

};


function sendMessage() {

const input =
document.getElementById(
'msg'
);


const text =
input.value;


if (!text)
return;


history.innerHTML +=

`

<div class="message user-msg">

<b>You</b>

<div>

${text}

</div>

</div>

`;


ws.send(text);


input.value = '';


history.scrollTop =
history.scrollHeight;

}

</script>

</body>

</html>

"""


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health")

def health():

    return {

        "status": "healthy",

        "service":
        "Coffee Shop AI Manager"

    }


# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":

    import uvicorn

    port_val = int(
        os.environ.get(
            "PORT",
            8000
        )
    )

    uvicorn.run(

        app,

        host="0.0.0.0",

        port=port_val

        )
