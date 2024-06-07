from flask import Flask, request, render_template
import openai
import os

app = Flask(__name__)

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def main():
    return render_template('main.html')

@app.route('/form', methods=['GET', 'POST'])
def info():
    if request.method == 'POST':
        age = request.form.get("age")
        gender = request.form.get("gender")
        height = request.form.get("height")
        weight = request.form.get("weight")
        activity = request.form.get("activity")
        
        # 입력값 검증
        try:
            height = int(height)
            weight = int(weight)
            age = int(age)
        except ValueError:
            return "숫자를 입력해주세요"
        
        # BMR 계산
        if gender == 'male':
            bmr = 88.4 + (13.4 * weight) + (4.8 * height) - (5.68 * age)
        elif gender == 'female':
            bmr = 447.6 + (9.25 * weight) + (3.1 * height) - (4.33 * age)
        else:
            return "성별을 체크해주세요"
        
        activity_factor = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        tdee = bmr * activity_factor.get(activity, 1.2)
        
        return render_template('result.html', bmr=f"{bmr:.2f}", tdee=f"{tdee:.2f}")
       
    return render_template('form.html')

def generate_meal_plan(tdee):
    # 1. 사용자의 TDEE를 기반으로 식단 계획을 생성하는 프롬프트 설정
    prompt = (f"아침, 점심, 저녁, 간식으로 나누어 주세요.\n"
              "앞에 **아침:**, **점심:**, **저녁:**, **간식:**으로 나눈 텍스트는 출력하지 말아주세요.\n"
              "식단은 각 끼니마다 음식 이름과 각 음식의 칼로리, 탄수화물, 단백질, 지방 함량을 포함해야 합니다.\n"
              f"하루 {tdee} kcal를 섭취하기 위한 탄단지 비율에 맞는 식단을 추천해줘")
    
    # 2. GPT 모델을 사용하여 식단 계획 생성
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=500,
    )
    meal_plan_raw = response.choices[0].message['content']
    
    # 3. 생성된 식단 계획을 저장할 딕셔너리 초기화
    meal_plan = {
        'morning': '',
        'lunch': '',
        'dinner': '',
        'snack': ''
    }
    
    # 4. 생성된 텍스트를 분석하여 각 식단에 맞게 분류
    sections = meal_plan_raw.split('\n')
    current_meal = None
    
    # 5. 해당 식단에 대한 정보를 딕셔너리에 저장
    for line in sections:
        if '아침' in line:
            current_meal = 'morning'
            meal_plan[current_meal] = line + '\n'
        elif '점심' in line:
            current_meal = 'lunch'
            meal_plan[current_meal] = line + '\n'
        elif '저녁' in line:
            current_meal = 'dinner'
            meal_plan[current_meal] = line + '\n'
        elif '간식' in line:
            current_meal = 'snack'
            meal_plan[current_meal] = line + '\n'
        elif current_meal:

            meal_plan[current_meal] += line + '\n'
            
    return meal_plan

@app.route("/generate_meal_plan", methods=["POST"])
def generate_meal_plan_route():
    # 1. 사용자로부터 TDEE 값 받아오기
    tdee = request.form["tdee"]
    
    # 2. TDEE 값을 기반으로 식단 계획 생성
    meal_plan = generate_meal_plan(tdee)
    # 3. 생성된 식단 계획을 템플릿으로 전달하여 웹 페이지에 표시
    return render_template("airecommand.html", 
                           meal_plan_morning=meal_plan['morning'],
                           meal_plan_lunch=meal_plan['lunch'],
                           meal_plan_dinner=meal_plan['dinner'],
                           meal_plan_snack=meal_plan['snack'])

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
      if request.method == 'POST':
        # 사용자가 입력한 데이터 수집
        age = request.form.get('age')
        gender = request.form.get('gender')
        height = request.form.get('height')
        weight = request.form.get('weight')
        activity = request.form.get('activity')
        goal = request.form.get('goal')
        morning = request.form.get('morning')
        lunch = request.form.get('lunch')
        dinner = request.form.get('dinner')
        
        activity_labels = {'1': '주로 앉아있음', '2': '보통', '3': '활동량 많음'}
        goal_labels = {'1': '체중 감량', '2': '체중 유지', '3': '체중 증가'}

        activity_text = activity_labels.get(activity, '알 수 없음')
        goal_text = goal_labels.get(goal, '알 수 없음')

        # 사용자 입력을 기반으로 GPT-3.5에 전달할 프롬프트 생성
        user_info = f"나이: {age}, 성별: {gender}, 키: {height}cm, 체중: {weight}kg, 활동 수준: {activity_text}, 목표: {goal_text}"
        diet_info = f"아침: {morning}, 점심: {lunch}, 저녁: {dinner}"

        System_Role = "이 사용자의 식단에 대해 구체적이고 실용적인 조언을 해주세요."
        prompt = f"사용자 정보: {user_info}를 고려하고 \n사용자의 식단: {diet_info}\n을 참고해서 사용자의 목표를 이루기 위해 사용자의 식단에 대해 어떤 조언을 해줄 수 있을까요?"

        # OpenAI GPT-3.5 API 호출
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages = [
                 {"role": "system", "content": System_Role},
                 {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature = 0.7
        )

        feedback_content = response.choices[0].message.content

        # 피드백 결과를 피드백 페이지에 전달
        return render_template('feedback.html', feedback=feedback_content)
    
      return render_template('feedback.html')

if __name__ == '__main__':
    app.run(debug=True)
