import os
import json
import requests
import uvicorn
from typing import Annotated
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


async def map_context(user_input):
    """maps input string with keywords and questions"""
    with open("FAQ.json", "r", encoding="utf-8") as handle:
        map_gen = (val for val in json.load(handle))

    context = ""
    user_input = user_input.lower().strip().replace('"', "")
    for q in map_gen:
        keywords = q["Keywords"]
        match_count = list(
            map(lambda x: x if x.lower() in user_input else None, keywords)
        )
        match_count = len([val for val in match_count if val != None])
        if match_count >= 1:
            print(match_count)
            print(q["Question ID"])
            if user_input == q["Question_original"].lower().replace(
                "?", ""
            ) or user_input == q["Question_short"].lower().replace("?", ""):
                context = q["Answer_plain_text"].replace("\\n", "")
                return user_input, context
            questions = [
                q["Question_original_alternatives"],
                q["Question_short_alternatives"],
            ]
            for qs in questions:
                match = list(
                    map(
                        lambda x: x
                        if x.lower().replace("?", "") == user_input
                        else None,
                        qs,
                    )
                )
                is_match = len([val for val in match if val != None])
                if is_match > 0:
                    context = q["Answer_plain_text"].replace("\\n", "")
                    return user_input, context
    return user_input, context


async def fetch_answer(query, params=None):
    """sends question and context"""
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json;charset=UTF-8",
    }
    if query[1]:
        context = [
            {"role": "user", "content": query[0]},
            {"role": "system", "content": query[1]},
        ]
    else:
        context = [{"role": "user", "content": query[0]}]

    params = {"model": "gpt-3.5-turbo", "messages": context}

    response = requests.post(api_url, json=params, headers=headers)
    status_code = response.status_code
    print(status_code)
    resp_body = response.json()
    if status_code in range(200, 399):
        try:
            resp_body = resp_body["choices"][0]["message"].get("content")
        except Exception as e:
            print(e)
    print(resp_body)
    return resp_body


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    context = {"request": request, "response": ""}
    return templates.TemplateResponse("index.html", context)


@app.post("/index/{query}")
async def get_data(query: Annotated[str, Query(min_length=2, max_length=500)] = ...):
    if query:
        query = await map_context(query)
        response = await fetch_answer(query)
    else:
        response = f"Could not process input: {query}"
    return response


if __name__ == "__main__":
    uvicorn.run(app)
