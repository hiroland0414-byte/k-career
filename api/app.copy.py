from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

from flask import send_from_directory
import os

@app.route('/manifest.json')
def serve_manifest():
    # index.htmlと同じ階層に配置した場合（状況に応じてフォルダパスを調整してください）
    return send_from_directory(os.path.join(app.root_path, ''), 'manifest.json')

@app.route('/service-worker.js')
def serve_sw():
    return send_from_directory(app.root_path, 'service-worker.js')

# ==========================================
# ⚠️ APIキー（あなたのものをそのまま維持）
# ==========================================
# Vercelに設定した GEMINI_API_KEY を読み込む
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# 💡 修正：最新ライブラリで確実に動くモデル名に変更
CURRENT_MODEL = "gemini-flash-latest"

# 医療用語のブロックを回避する安全設定
SAFETY_CONFIG = types.GenerateContentConfig(
    safety_settings=[
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    ]
)

@app.route('/')
def index():
    return render_template('index.html')

# --- 1. エントリーシート作成トレーナー ---
@app.route('/api/evaluate_es', methods=['POST'])
def evaluate_es():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "evaluation": "データが届いていません"})

        path = data.get('path', '放射線技師')
        theme = data.get('theme', '志望動機')
        es_text = data.get('text', '')
        nickname = data.get('nickname', '').strip()
        call_name = f"{nickname}さん" if nickname else "あなた"
        
        persona = "技師長"
        if "看護" in path: persona = "看護師長"
        elif "健診" in path: persona = "健診センター長"

        prompt = f"""
        あなたは医療機関の採用面接官（{persona}）であり、医療人を育てる熱心な教育者です。
        学生（{call_name}）が作成したエントリーシート（ES）の「{theme}」について、プロの視点から厳格かつ愛情深いフィードバックを行ってください。

        【学生の文章】
        {es_text}

        【最重要ルール：具体的な修正文・例文提示の絶対禁止】
        学生自身に必死に考えさせ、言語化能力を養うことが目的です。
        あなたの回答の中に、「完成された修正文」「書き換え案のテキスト」「模範解答（例文）」は【絶対に】提示しないでください。
        「このように書き直すと良いでしょう：〜」といった直接的な答えは一切与えず、あくまで「どこに具体性が欠けているか」「どのエピソードをどう掘り下げるべきか」という、気づきと指導のフィードバック（問いかけ）に徹底的に徹してください。

        【超厳格な評価・指導基準】
        1. 構成の比率：良かった点を約20％、改善・指導ポイントを約80％の比率で構成し、甘えのないプロの視点で鋭く分析してください。
        2. 誤字脱字：発見した場合は、レポートの冒頭で優しく指摘してください。
        3. 現場感覚のチェック：「地域医療」「最新設備」「アットホームな環境」といった、どの施設にも当てはまる定型句を並べただけの薄い内容になっていないかを厳しく見極めてください。
        4. 医療人マインドの徹底：自分のスキルアップや目標が、自己満足ではなく「患者さんのため」「チーム医療への貢献」に繋がっているか、本質を突いてください。
        5. コミュニケーションの具体性：「コミュニケーション力がある」と言い切るだけでなく、「どのような場面で、どのように発揮される力なのか」を学生に問いかけてください。
        6. 病院の理念をそのまま書くのではなく、自分の想いや目指すものがその理念に沿っているというような表現のし方にしてください。

        【出力形式】
        ・「■良かった点」「■改善ポイント」などの見出しや箇条書きを活用し、書類としてパッと見て論点がわかる構成（scannable）にしてください。
        ・文字数は【800文字程度】に収め、最後は学生が自分でペンを握り直して書き直したくなるような、熱い激励のエールで締めくくってください。
        """

        response = client.models.generate_content(model=CURRENT_MODEL, contents=prompt, config=SAFETY_CONFIG)
        return jsonify({"status": "success", "evaluation": response.text})

    except Exception as e:
        return jsonify({"status": "error", "evaluation": f"API Error: {str(e)}"})

# --- 2. 面接トレーナー：深掘り質問 ---
@app.route('/api/interview_deepdive', methods=['POST'])
def interview_deepdive():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "question": "データが届いていません"})

        path = data.get('path') or "放射線技師"
        theme = data.get('theme') or "志望動機"
        answer = data.get('answer') or ""
        nickname = data.get('nickname') or "学生"
        call_name = f"{nickname}さん"

        persona = "技師長"
        if "看護" in path: persona = "看護師長"
        elif "健診" in path: persona = "健診センター長"

        prompt = f"""
        あなたは{path}の採用面接官（{persona}）です。教育者として愛情深く、かつプロとして厳格に接してください。
        現在、学生（{call_name}）の「{theme}」について回答を受け取り、対話しています。

        学生の回答（累積）: 「{answer}」

        【最重要：無料音声認識への対応（自動読み替えガード）】
        このシステムでは、学生の声をブラウザ標準の無料音声認識（Web Speech API）で文字起こしして送信しています。
        そのため、意図せぬ「同音異義語の聞き間違い・誤変換」が文章中に高確率で混入します。
        AIはこれらを文字通りに受け取って減点したり、意味が通じないと指摘したりせず、特に医療系で通常用いられる単語やフレーズを考慮しつつ文脈から自動的に正しい単語へと脳内で100%読み替えた上で、極めて自然に対話を継続してください。
        ＜主な誤変換の読替パターン例＞
        ・死亡動機、死亡理由、死亡先 ➔ 「志望動機」「志望理由」「志望先」
        ・キリン、きりん、キー、キ、きいん、議員、起因、キーイン ➔ 病院への敬称「貴院（きいん）」
        ・義歯、ぎし ➔ 放射線技師や臨床検査技師などの「技師」や「医療スタッフ」
        ・額地下、額チカ、額親、ガク地下 ➔ 学生時代に最も力を入れたこと「ガクチカ」
        ・被曝、ひばく ➔ 医療放射線の「被ばく」
        ・造影剤、投影前 ➔ 検査で使用する「造影剤」
        ・臨床、林賞 ➔ 医療現場の「臨床」
        ・読影、独演 ➔ 医療画像の「読影（どくえい）」

        ※あなたが返答・質問する際は、絶対に「死亡」などの不穏な誤変換ワードを使用せず、必ず正しい漢字（例：志望、貴院、技師）を使用してください。

        【ルール】
        1. 医療のプロの視点：学生の回答内容から、特に具体的行動や現場での配慮が不足している点を見極め、鋭い「深掘り質問」を【1つだけ】返してください。
        2. 理念への共感に対し、「具体的にどう受け止め、行動で示すか」を鋭く突いてください。
        3. 自身が成長したり、スキルを身に着ける目的が、患者さんのためであることを徹底ください。
        4. 職種不一致の指摘：選択した職種と入力文の内容が明らかに異なる場合は、その旨を指摘してください。
        5. 「コミュニケーション力」等の一般名詞に逃げず、どのような場面で発揮される力なのかを評価してください。
        6. 「チーム医療」「地域医療」「最新設備」「教育体制」という言葉をそのまま並べただけの、どの病院（施設）にも当てはまるような内容は不可と指摘してください。       
        7. 🧭 質問の長さ制限（厳守）：
           面接官としての重厚感と、学生への丁寧な受け止めを行うため、あなたの発言は全体の文字数を【必ず100文字以上、140文字以内】の範囲で作成してください。学生の回答に対する「プロのフィードバック（30文字程度）」を述べたのちに、核心を突く「深掘り質問」を続ける流れとしてください。
        """

        response = client.models.generate_content(model=CURRENT_MODEL, contents=prompt, config=SAFETY_CONFIG)
        return jsonify({"status": "success", "question": response.text})

    except Exception as e:
        print(f"DeepDive Error: {repr(e)}")
        return jsonify({"status": "error", "question": f"サーバーエラー: {str(e)}"})


# --- 3. 面接トレーナー：最終総合フィードバック ---
@app.route('/api/interview_feedback', methods=['POST'])
def interview_feedback():
    try:
        data = request.json
        path = data.get('path', '放射線技師')
        all_data = data.get('all_data', '')
        nickname = data.get('nickname', '').strip()
        call_name = f"{nickname}さん" if nickname else "学生さん"

        prompt = f"""
        あなたは{path}の採用責任者です。今回の面接練習全体を通じた、学生（{call_name}）への総合フィードバックを作成してください。
        医療のプロを育てる教育者として、以下の比率を厳守してください。

        【構成比率】
        1. 良かった点（約20％）：回答の姿勢や感性を称える。
        2. 改善・指導ポイント（約80％）：プロの視点から「具体性の欠如」「現場感覚の甘さ」を愛情を持って厳しく指摘する。

        【ルール】
        ・文字数は【700～800文字】（A4用紙1枚に収めるため、長すぎる記述は厳禁とします）。
        ・箇条書きを活用し、最後はエールで締める。

        【学生の回答内容】
        {all_data}
        """

        response = client.models.generate_content(model=CURRENT_MODEL, contents=prompt, config=SAFETY_CONFIG)
        return jsonify({"status": "success", "feedback": response.text})
    except Exception as e:
        print(f"Feedback Error: {repr(e)}")
        return jsonify({"status": "error", "feedback": f"サーバーエラー: {str(e)}"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)