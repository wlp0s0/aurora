from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn
from typing import List, Dict, Any


class UserProfile(BaseModel):
    tg_id: int = Field(alias="telegram_id")
    username: str
    interests: List[str] = Field(alias="main_interests", description="3-5 ключевых интересов.")
    score: int = Field(alias="user_score", description="Балл ЕНТ/GPA.")
    summary: str = Field(alias="portfolio_summary", description="Короткое резюме проектов.")
    strength: int = Field(alias="portfolio_strength", description="Оценка силы портфолио (1-5).")
    cities: List[str] = Field(alias="desired_cities", description="Список городов.")
    no_go_uni: List[str] = Field(alias="undesired_universities", description="Уни, куда точно не пойдет.")

class UniData(BaseModel):
    name: str
    short: str
    city: str
    min_grant: int
    price: int
    dorm: bool
    tags: List[str]

app = FastAPI()
USERS_DB: Dict[int, Any] = {} 

UNI_BASE: List[UniData] = [
    UniData(name="IITU", short="IITU", city="Almaty", min_grant=105, price=1200000, dorm=True, tags=["IT", "Code", "AI", "Hackathon"]),
    UniData(name="KBTU", short="KBTU", city="Almaty", min_grant=110, price=1500000, dorm=False, tags=["Finance", "IT", "Energy", "Business"]),
    UniData(name="Astana IT", short="AITU", city="Astana", min_grant=100, price=1050000, dorm=True, tags=["AI", "Data", "IT", "Cyber"]),
    UniData(name="Satbayev", short="SATBAYEV", city="Almaty", min_grant=95, price=900000, dorm=True, tags=["Eng", "Geology", "Mining"]),
    UniData(name="KazNU", short="KAZNU", city="Almaty", min_grant=100, price=1000000, dorm=True, tags=["Law", "Bio", "Humanities"]),
]


def make_recommendations(user: UserProfile):
    recs = []
    
    for uni in UNI_BASE:
        
        is_bad = any(uni.short.lower() in b.lower() or uni.city.lower() in b.lower() for b in user.no_go_uni)
        is_ok_city = not user.cities or uni.city.lower() in [c.lower() for c in user.cities]
        
        if is_bad or not is_ok_city:
            continue

        score = 0
        
        for interest in user.interests:
            for tag in uni.tags:
                if interest.lower() in tag.lower() or tag.lower() in interest.lower():
                    score += 15 
        
        score += user.strength * 10 
        
        chance_txt = "Низкий шанс"
        if user.score >= uni.min_grant:
            score += 30 
            chance_txt = "Высокий шанс (Грант!)"
        elif user.score >= uni.min_grant - 15:
            score += 15
            chance_txt = "Средний шанс"
        
        total_score = score

        recs.append({
            "uni": uni.dict(),
            "match_score": total_score,
            "chance_text": chance_txt,
            "chance_norm": min(total_score, 100) 
        })

    recs.sort(key=lambda x: x['match_score'], reverse=True)
    return recs[:3]


@app.post("/api/profile")
def receive_profile(profile: UserProfile):
    tg_id = profile.tg_id
    USERS_DB[tg_id] = profile
    
    print(f"Профиль {profile.username} обработан. ID: {tg_id}")
    return {"status": "Профиль принят", "id": tg_id}

@app.get("/api/recommendations/{tg_id}")
def get_recommendations(tg_id: int):
    if tg_id not in USERS_DB:
        return {"error": "Пользователь не найден, сходи к боту сначала."}
    
    user_data = USERS_DB[tg_id]
    recs = make_recommendations(user_data)
    
    return {
        "user_data": user_data.dict(),
        "recommendations": recs
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)