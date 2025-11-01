from flask import Flask, render_template, request
import os
from dotenv import load_dotenv
import google.generativeai as genai
from markupsafe import Markup
import re

load_dotenv()
app = Flask(__name__)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def build_prompt(conversation, tone):
    tone_instruction = {
        "default": "モテの先生のように教えてください",
        "male": "解説は男らしい、頼りになる先輩のようにしてください。",
        "female": "解説はやわらかく、女友達のようにしてください。"
    }

    formatted_convo = ""
    for i, (user, partner) in enumerate(conversation):
        if user.strip():
            formatted_convo += f"自分：{user.strip()}\n"
        if partner.strip():
            formatted_convo += f"相手：{partner.strip()}\n"

    prompt = f"""
あなたは大学生向けの恋愛LINE添削AIです。
以下のやりとりを見て、モテる返信案を3パターン提案してください。
それぞれの返信がなぜ良いのか簡単に解説してください。
絵文字は基本入れないで。笑にかっこはつけないで。
長文は怖いから長くても2,3文にして。
{tone_instruction.get(tone, "")}

【LINE会話】
{formatted_convo}

出力形式：（絶対にこの順で）
1. モテ返信案A：
   解説：
2. モテ返信案B：
   解説：
3. モテ返信案C：
   解説：
"""
    return prompt

def extract_reply_bubbles_and_explanations(response_text):
    replies = []
    explanations = []

    blocks = re.findall(
        r"(\d+\.\s*モテ返信案[ABC]：(?:.|\n)*?)(?=\n\d+\.\s*モテ返信案[ABC]：|\Z)", 
        response_text.strip()
    )

    for block in blocks:
        reply_number = ""
        reply_text = ""
        explanation_text = ""

        match = re.search(r"(\d+\.\s*モテ返信案[ABC]：)", block)
        if match:
            reply_number = match.group(1).strip()

        if "解説：" in block:
            parts = block.split("解説：", 1)
            reply_section = parts[0]
            explanation_text = parts[1].strip()
        else:
            reply_section = block

        match_reply = re.search(r"(「.*?」)", reply_section)
        if match_reply:
            reply_text = match_reply.group(1)
        else:
            lines = reply_section.strip().split("\n")
            if len(lines) >= 2:
                reply_text = lines[1].strip()
            elif len(lines) == 1:
                reply_text = lines[0].replace(reply_number, "").strip()

        if reply_text:
            bubble_html = f'''
            <div class="message-row user">
              <div class="chat-bubble user">{Markup(reply_text)}</div>
              <img src="/static/images/user_icon.png" class="icon">
            </div>
            '''
            replies.append(bubble_html)

        if reply_number and explanation_text:
            explanations.append(f"{reply_number}<br>{explanation_text.strip()}")

    bubbles_html = "\n".join(replies)
    explanation_html = "<ol>" + "".join(
        [f"<li>{Markup(exp)}</li>" for exp in explanations]
    ) + "</ol>"

    return Markup(bubbles_html), Markup(explanation_html)

@app.route("/", methods=["GET", "POST"])
def index():
    response_text = ""
    bubbles_html = ""
    explanations_html = ""
    if request.method == "POST":
        conversation = []
        i = 0
        while True:
            user_key = f"user_line_{i}"
            partner_key = f"partner_line_{i}"
            if user_key not in request.form and partner_key not in request.form:
                break
            user_line = request.form.get(user_key, "")
            partner_line = request.form.get(partner_key, "")
            conversation.append((user_line, partner_line))
            i += 1

        tone = request.form.get("tone", "default")
        prompt = build_prompt(conversation, tone)
        response = model.generate_content(prompt)
        response_text = response.text

        bubbles_html, explanations_html = extract_reply_bubbles_and_explanations(response_text)

    return render_template(
        "index.html",
        response=response_text,
        bubbles=bubbles_html,
        explanations=explanations_html
    )

if __name__ == "__main__":
    app.run(debug=True)