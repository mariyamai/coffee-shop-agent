import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from groq import Groq

app = FastAPI(title="Coffee Shop AI Agent")

# Get Groq API key from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set!")

client = Groq(api_key=GROQ_API_KEY)


@app.get("/", response_class=HTMLResponse)
async def home():

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Coffee Shop AI Agent</title>

        <style>

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f5efeb;
        }

        #header {
            background: #3E2723;
            color: white;
            padding: 20px;
            text-align: center;
        }

        #chat {
            height: 70vh;
            overflow-y: auto;
            padding: 20px;
        }

        .message {
            padding: 12px;
            margin: 10px;
            border-radius: 10px;
            max-width: 80%;
        }

        .user {
            background: #d7ccc8;
            margin-left: auto;
        }

        .agent {
            background: white;
        }

        #input-area {
            display: flex;
            padding: 20px;
            background: white;
        }

        input {
            flex: 1;
            padding: 12px;
            font-size: 16px;
        }

        button {
            padding: 12px 25px;
            background: #6D4C41;
            color: white;
            border: none;
            margin-left: 10px;
            border-radius: 5px;
        }

        </style>

    </head>

    <body>

        <div id="header">
            <h2>☕ Coffee Shop AI Agent</h2>
        </div>

        <div id="chat"></div>

        <div id="input-area">

            <input
                id="message"
                placeholder="Ask the Coffee Shop Agent..."
                onkeypress="if(event.key === 'Enter') sendMessage()"
            >

            <button onclick="sendMessage()">Send</button>

        </div>


        <script>

        const protocol =
            window.location.protocol === "https:" ? "wss:" : "ws:";

        const ws = new WebSocket(
            `${protocol}//${window.location.host}/ws`
        );

        const chat = document.getElementById("chat");


        ws.onmessage = function(event) {

            chat.innerHTML += `
                <div class="message agent">
                    <b>☕ AI Agent:</b><br>
                    ${event.data}
                </div>
            `;

            chat.scrollTop = chat.scrollHeight;

        };


        function sendMessage() {

            const input =
                document.getElementById("message");

            const text = input.value;

            if (!text) return;


            chat.innerHTML += `
                <div class="message user">
                    <b>You:</b><br>
                    ${text}
                </div>
            `;


            ws.send(text);

            input.value = "";

            chat.scrollTop = chat.scrollHeight;

        }

        </script>

    </body>
    </html>
    """


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    try:

        while True:

            user_message = await websocket.receive_text()


            completion = client.chat.completions.create(

                model="llama-3.3-70b-versatile",

                messages=[
                    {
                        "role": "system",
                        "content": """
You are a helpful AI Business Analyst for a coffee shop.

Help the manager analyze:
- Coffee sales
- Busy periods
- Staffing
- Inventory
- Customer wait times

Give practical and clear recommendations.
"""
                    },

                    {
                        "role": "user",
                        "content": user_message
                    }
                ]

            )


            response = completion.choices[0].message.content


            await websocket.send_text(response)


    except WebSocketDisconnect:

        print("User disconnected")


if __name__ == "__main__":

    import uvicorn

    port = int(os.getenv("PORT", 8080))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
            )
