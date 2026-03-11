from fastapi import APIRouter
from app_registry import app_register
import os
import httpx

router = app_register.register_router(APIRouter(prefix="/test", tags=["test"]))

@router.get("/")
async def test():
    return {"message" : "test server rout"}


@router.get("/tavily")
async def tavily():
    from tavily import TavilyClient

    tavily_client = TavilyClient()
    response = tavily_client.search(
        query = "Who is Leo Messi?",
        # search_depth = "basic"
    )

    # {
    #     "query": "Who is Leo Messi?",
    #     "response_time": 0.96,
    #     "follow_up_questions": null,
    #     "answer": null,
    #     "images": [],
    #     "results": [
    #         {
    #         "url": "https://www.intermiamicf.com/players/lionel-messi/",
    #         "title": "Lionel Messi | Inter Miami CF",
    #         "content": "# Lionel Messi. Leo Messi Named MLS Player of the Matchday presented by Michelob ULTRA for Matchday 2. ## Leo Messi Named MLS Player of the Matchday presented by Michelob ULTRA for Matchday 2. Inter Miami CF captain Lionel Messi’s standout performance against Orlando City SC on Sunday night earn him Major League Soccer (MLS) Player of the Matchday presented by Michelob ULTRA honors for Matchday 2. Inter Miami CF Academy U-16s Complete Messi Cup Campaign. ## Inter Miami CF Academy U-16s Complete Messi Cup Campaign. Leo Messi Named MVP, Jordi Alba Named Defensive MVP as Inter Miami CF Announces Club Awards. ## Leo Messi Named MVP, Jordi Alba Named Defensive MVP as Inter Miami CF Announces Club Awards. Inter Miami CF Captain Leo Messi Named 2025 Landon Donovan MLS Most Valuable Player. ## Inter Miami CF Captain Leo Messi Named 2025 Landon Donovan MLS Most Valuable Player. New York City site address. Red Bull New York site address.",
    #         "score": 0.99648935,
    #         "raw_content": null
    #         },
    #         {
    #         "url": "https://www.britannica.com/biography/Lionel-Messi",
    #         "title": "Lionel Messi | Biography, Trophies, Records, Ballon d'Or ... - Britannica",
    #         "content": "Lionel Messi scored 73 goals during the 2011–12 season while playing for FC Barcelona, breaking a 39-year-old record for single-season goals in a major European football league. Messi’s play continued to rapidly improve over the years, and by 2008 he was one of the most dominant players in the world, finishing second to Manchester United’s Cristiano Ronaldo in the voting for the 2008 Ballon d’Or. In early 2009 Messi capped off a spectacular 2008–09 season by helping FC Barcelona capture the club’s first “treble” (winning three major European club titles in one season): the team won the La Liga championship, the Copa del Rey (Spain’s major domestic cup), and the Champions League title. Messi helped Barcelona capture another treble during the 2014–15 season, leading the team with 43 goals scored over the course of the campaign, which resulted in his fifth world player of the year honor.",
    #         "score": 0.98228765,
    #         "raw_content": null
    #         },
    #         {
    #         "url": "https://messi.com/en/biography/",
    #         "title": "Biografía Leo Messi | messi.com",
    #         "content": "We all played football — it was the most important thing in our lives. I left when I was 13, way before I started playing for Barcelona, a team which I had been following for a long time. When I arrived in Barcelona, my dream was to play in the first team, but I never could’ve imagined what would happen next! I’ve always wanted to play for the national team and living far away made that dream even stronger. But one day, when I was sixteen, I was called up to play in two friendlies with the U- 20 team against Paraguay and Uruguay — the beginning of my journey. I still love playing football, but when the match is over I dedicate that time to my family. I want to thank everyone who has supported me all this time: Those who believe, like me, that great things are yet to be achieved.",
    #         "score": 0.97719735,
    #         "raw_content": null
    #         },
    #         {
    #         "url": "https://www.olympics.com/en/athletes/lionel-messi",
    #         "title": "Lionel Messi | Biography, Competitions, Wins and Medals",
    #         "content": "### Lionel Messi at FIFA World Cup: Biggest disappointments of Argentina superstar. Born in Rosario, Argentina, in 1987, **Lionel Messi** is widely regarded as one of the greatest football players of all time, and his illustrious career proves why. [Football](https://www.olympics.com/en/news/erling-haaland-how-does-the-striker-compare-to-messi-ronaldo-mbappe). FIFA World Cup 2022: What records did Lionel Messi break? [Lionel MESSI](https://www.olympics.com/en/news/fifa-world-cup-2022-lionel-messi-records). ### FIFA World Cup 2022: What records did Lionel Messi break? Lionel Messi at FIFA World Cup: Biggest disappointments of Argentina superstar. [Lionel MESSI](https://www.olympics.com/en/news/lionel-messi-fifa-world-cup-biggest-disappointments). These Cookies allow us to count visits and traffic sources so we can measure and improve the performance of our Service. If you do not allow these cookies we will not know when you have used our Service. Functional cookies that enhance the functionality and personalisation of our Service by storing your preferences. If you do not allow these Cookies, then some or all of the services available may not function properly.",
    #         "score": 0.9759464,
    #         "raw_content": null
    #         },
    #         {
    #         "url": "https://en.wikipedia.org/wiki/Lionel_Messi",
    #         "title": "Lionel Messi - Wikipedia",
    #         "content": "Rodríguez * MF: Krychowiak * MF: Rakitić * FW: Messi * FW: Ronaldo * FW: Griezmann * Manager: Luis Enrique | | * v * t * e 2015–16 La Liga Team of the Year | | --- | | * GK: Oblak * RB: Ramos * CB: Piqué * CB: Godín * LB: Marcelo \"Marcelo (footballer, born 1988)\") * MF: Iniesta * MF: Busquets * MF: Modrić * FW: Messi * FW: Ronaldo * FW: Suárez | | * v * t * e 2022–23 Ligue 1 UNFP Team of the Year | | --- | | * GK: Samba * DF: Hakimi * DF: Mbemba * DF: Danso * DF: Mendes \"Nuno Mendes (footballer, born 2002)\") * MF: Thuram * MF: Rongier * MF: Fofana * FW: Messi * FW: Openda * FW: Mbappé | | * v * t * e 2024 MLS Best XI | | --- | | * GK: Kahlina * DF: Alba * DF: Gómez * DF: Moreira * MF: Acosta * MF: Evander \"Evander (footballer)\") * MF: Puig * FW: Benteke * FW: Bouanga * FW: Hernández * FW: Messi | | * v * t\") * e 2025 MLS Best XI | | --- | | * GK: St. Clair * DF: Blackmon * DF: Freeman * DF: Glesnes * DF: Wagner * MF: Berhalter * MF: Evander \"Evander (footballer)\") * MF: Roldan * FW: Bouanga * FW: Dreyer * FW: Messi | | * v * t * e *Sports Illustrated* Soccer 2000s All-Decade Team | | --- | | Goalkeeper \"Goalkeeper (association football)\") | * Gianluigi Buffon | | Defenders \"Defender (association football)\") | * Cafu * Fabio Cannavaro * Paolo Maldini * Roberto Carlos | | Midfielders | * Cristiano Ronaldo * Zinedine Zidane * Patrick Vieira * Lionel Messi * Ronaldinho | | Forwards \"Forward (association football)\") | | | Manager \"Manager (association football)\") | * Guus",
    #         "score": 0.9635062,
    #         "raw_content": null
    #         }
    #     ],
    #     "request_id": "b4109503-121c-4854-abaa-1124d1eb4798"
    # }

    return response

# -------------Duckling 테스트-------------------
@router.get("/duckling")
async def duckling(query: str):
    try:
        DUCKLING_URL = os.getenv("DUCKLING_URL", "http://duckling:8000")

        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{DUCKLING_URL}/parse",
                data={   # ✅ form-urlencoded
                    "text": query,
                    "locale": "ko_KR",
                    "tz": "Asia/Seoul",
                    "dims": '["time"]'   # 중요: 문자열 JSON
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )

            res.raise_for_status()
            data = res.json()

            #  출력 예시
            # [
            #     {
            #         "body": "3일전",
            #         "start": 0,
            #         "value": {
            #         "values": [
            #             {
            #             "value": "2026-03-08T10:00:00.000+09:00",
            #             "grain": "hour",
            #             "type" : "value"
            #             }
            #         ],
            #         "value": "2026-03-08T10:00:00.000+09:00",
            #         "grain": "hour",
            #         "type": "value"
            #         },
            #         "end": 3,
            #         "dim": "time",
            #         "latent": false
            #     }
            # ]
            print("-"*100)
            print(data)
            print("-"*100)

            return {"query" : query, "result" : data[0]["value"]["value"]}

    except Exception as e:
        return {"error" : str(e)}
    finally:
        await client.aclose()

