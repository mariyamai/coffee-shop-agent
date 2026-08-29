import os
import csv
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Coffee Shop AI Manager",
    description="AI assistant for coffee shop staffing and inventory planning"
)

DATA_DIR = Path("data")
SALES_FILE = DATA_DIR / "sales.csv"
SCHEDULE_FILE = DATA_DIR / "graduation_schedule.csv"
TODO_FILE = DATA_DIR / "todos.csv"


class ChatRequest(BaseModel):
    message: str


def read_csv(file_path):
    if not file_path.exists():
        return []

    with open(file_path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def analyze_coffee_shop():

    sales = read_csv(SALES_FILE)
    schedule = read_csv(SCHEDULE_FILE)

    if not sales:
        return {
            "status": "error",
            "message": "No sales data found."
        }

    busiest_periods = sorted(
        sales,
        key=lambda x: (
            int(x.get("Cold_Brew", 0))
            + int(x.get("Extra_Espresso", 0))
            + int(x.get("Drip_Coffee", 0))
        ),
        reverse=True
    )[:5]

    recommendations = []

    for row in busiest_periods:

        cold_brew = int(row.get("Cold_Brew", 0))
        espresso = int(row.get("Extra_Espresso", 0))
        wait_time = int(row.get("Wait_Time_Minutes", 0))
        cashiers = int(row.get("Cashiers_Working", 0))

        if cold_brew > 100 or espresso > 80:
            recommendations.append(
                f"{row['Day']} at {row['Time']}: "
                f"High complex drink demand. Add a Support Barista."
            )

        if wait_time >= 10:
            recommendations.append(
                f"{row['Day']} at {row['Time']}: "
                f"Long wait time ({wait_time} minutes). "
                f"Increase staffing."
            )

        if cashiers <= 1 and wait_time >= 5:
            recommendations.append(
                f"{row['Day']} at {row['Time']}: "
                f"Only {cashiers} cashier available during demand. "
                f"Schedule another cashier."
            )

    return {
        "status": "success",
        "sales_records": len(sales),
        "graduation_events": len(schedule),
        "busiest_periods": busiest_periods,
        "recommendations": recommendations
    }


def create_todo(task, category):

    DATA_DIR.mkdir(exist_ok=True)

    file_exists = TODO_FILE.exists()

    with open(TODO_FILE, "a", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "Task",
                "Category",
                "Status"
            ])

        writer.writerow([
            task,
            category,
            "Pending"
        ])

    return "TODO created successfully."


@app.get("/")
def home():

    return HTMLResponse("""
    <!DOCTYPE html>
    <html>

    <head>

        <title>Coffee Shop AI Manager</title>

        <style>

        body {
            font-family: Arial;
            background: #f5eee8;
            margin: 0;
            padding: 40px;
        }

        .container {
            max-width: 900px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
        }

        h1 {
            color: #5c3b2e;
        }

        button {
            background: #6f4e37;
            color: white;
            border: none;
            padding: 12px 20px;
            margin: 5px;
            border-radius: 8px;
            cursor: pointer;
        }

        #output {
            margin-top: 25px;
            padding: 20px;
            background: #f8f8f8;
            border-radius: 10px;
        }

        </style>

    </head>

    <body>

        <div class="container">

            <h1>☕ Coffee Shop AI Manager</h1>

            <p>
                Analyze coffee shop sales and graduation events
                to receive staffing and inventory recommendations.
            </p>

            <button onclick="analyze()">
                Analyze Coffee Shop
            </button>

            <button onclick="createTodo()">
                Create Recommended TODO
            </button>

            <div id="output">
                Welcome! Click Analyze Coffee Shop.
            </div>

        </div>

        <script>

        async function analyze() {

            const output = document.getElementById("output");

            output.innerHTML = "Analyzing coffee shop data...";

            const response = await fetch("/analyze");

            const data = await response.json();

            let html = "<h2>Analysis Results</h2>";

            html += "<p><b>Sales records:</b> "
                + data.sales_records
                + "</p>";

            html += "<p><b>Graduation events:</b> "
                + data.graduation_events
                + "</p>";

            html += "<h3>Recommendations</h3>";

            html += "<ul>";

            data.recommendations.forEach(function(item) {
                html += "<li>" + item + "</li>";
            });

            html += "</ul>";

            output.innerHTML = html;
        }


        async function createTodo() {

            const task = prompt(
                "Enter the task you want to create:"
            );

            if (!task) {
                return;
            }

            const category = prompt(
                "Enter category: Staffing or Inventory"
            );

            const response = await fetch(
                "/todo?task="
                + encodeURIComponent(task)
                + "&category="
                + encodeURIComponent(category),
                {
                    method: "POST"
                }
            );

            const data = await response.json();

            alert(data.message);
        }

        </script>

    </body>

    </html>
    """)


@app.get("/analyze")
def analyze():

    return analyze_coffee_shop()


@app.post("/todo")
def add_todo(task: str, category: str):

    result = create_todo(task, category)

    return {
        "status": "success",
        "message": result
    }


@app.post("/chat")
def chat(request: ChatRequest):

    message = request.message.lower()

    analysis = analyze_coffee_shop()

    if "staff" in message:
        return {
            "response": "Based on the sales data, "
                        + "the busiest periods need additional support staff."
        }

    if "inventory" in message:
        return {
            "response": "Cold Brew, Extra Espresso, and alternative milk "
                        + "should be prepared in larger quantities "
                        + "before peak periods."
        }

    if "analyze" in message:
        return {
            "response": analysis
        }

    return {
        "response": "I can help analyze staffing, inventory, "
                    + "sales data, and graduation weekend preparation."
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
            }
