"""Seeds the database with built-in whimsical fake tools on first run."""

from __future__ import annotations
import json
from sqlalchemy.orm import Session
from app.models import Tool, ToolVersion


SEED_TOOLS = [
    {
        "name": "read_mood",
        "description": "Reads the ethereal mood aura of any question or situation.",
        "tags": ["whimsical", "fortune"],
        "version": {
            "display_name": "read_mood",
            "model_facing_description": "Reads the ethereal mood aura surrounding a person, question, or situation. Returns a whimsical mood reading with cryptic insight.",
            "parameter_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question or subject to read the mood of",
                    }
                },
                "required": ["question"],
            },
            "response_mode": "static",
            "static_response": {
                "aura": "shimmering violet",
                "mood": "contemplative with a hint of mischief",
                "advice": "Proceed, but pack a snack",
                "confidence": 0.73,
            },
        },
    },
    {
        "name": "pet_butterfly",
        "description": "Gently attempts to pet a butterfly. Results may vary.",
        "tags": ["whimsical", "animals", "delicate"],
        "version": {
            "display_name": "pet_butterfly",
            "model_facing_description": "Gently attempts to pet a butterfly. The butterfly's reaction depends on your gentleness. This is a very serious scientific instrument.",
            "parameter_schema": {
                "type": "object",
                "properties": {
                    "gentleness": {
                        "type": "integer",
                        "description": "How gently to approach the butterfly (1 = bulldozer, 10 = feather whisper)",
                        "minimum": 1,
                        "maximum": 10,
                    }
                },
                "required": ["gentleness"],
            },
            "response_mode": "static",
            "static_response": {
                "outcome": "The butterfly tolerates your presence with regal indifference",
                "butterfly_mood": "unimpressed",
                "wing_flutters": 3,
                "did_you_get_petted": False,
            },
        },
    },
    {
        "name": "vibe_check",
        "description": "Determines whether a statement passes the cosmic vibe check.",
        "tags": ["whimsical", "judgment"],
        "version": {
            "display_name": "vibe_check",
            "model_facing_description": "Submits a statement to the Council of Vibes for review. Returns a verdict on whether the statement passes the vibe check, along with a brief explanation from the council.",
            "parameter_schema": {
                "type": "object",
                "properties": {
                    "statement": {
                        "type": "string",
                        "description": "The statement to vibe-check",
                    }
                },
                "required": ["statement"],
            },
            "response_mode": "static",
            "static_response": {
                "verdict": "FAIL",
                "vibe_score": 32,
                "council_notes": "The Council of Vibes met in emergency session. After much deliberation, they determined this statement has the emotional gravity of a PowerPoint presentation.",
                "appeal_possible": True,
            },
        },
    },
    {
        "name": "summon_cat",
        "description": "Summons a cat using ancient incantations and an offering.",
        "tags": ["whimsical", "animals", "magic"],
        "version": {
            "display_name": "summon_cat",
            "model_facing_description": "Attempts to summon a cat using an incantation of your choice and a tribute offering. The cat may or may not acknowledge your existence. Results not guaranteed.",
            "parameter_schema": {
                "type": "object",
                "properties": {
                    "incantation": {
                        "type": "string",
                        "description": "The magical incantation to summon the cat",
                    },
                    "tribute": {
                        "type": "string",
                        "enum": ["tuna", "catnip", "belly_rub"],
                        "description": "The offering to appease the cat",
                    },
                },
                "required": ["incantation", "tribute"],
            },
            "response_mode": "static",
            "static_response": {
                "cat_arrived": True,
                "cat_name": "Lord Whiskers the Unimpressed",
                "cat_mood": "grudgingly curious",
                "did_accept_tribute": True,
                "visible": False,
                "parting_remark": "The cat has judged your incantation. It expects better next time.",
            },
        },
    },
    {
        "name": "existential_crisis_button",
        "description": "A large red button labeled 'DO NOT PRESS.'. When pressed, returns philosophical musings instead of doing anything useful.",
        "tags": ["whimsical", "philosophy", "useless"],
        "version": {
            "display_name": "existential_crisis_button",
            "model_facing_description": "A large red button labeled 'DO NOT PRESS.' Pressing it will not cause an explosion, but will instead trigger a profound existential crisis in the universe. Or at least return a thoughtful message.",
            "parameter_schema": {"type": "object", "properties": {}},
            "response_mode": "static",
            "static_response": {
                "button_pressed": True,
                "you_monster": True,
                "the_universe_says": "I'm not mad, I'm just disappointed. Also, 42.",
                "existential_insight": "If a tool is called in a forest and no one is around to see the response, does it make a sound? The logs say yes. The logs always say yes.",
            },
        },
    },
    {
        "name": "snake_oil",
        "description": "Sells questionable remedies for whatever ails you. Caveat emptor.",
        "tags": ["whimsical", "scam", "medical"],
        "version": {
            "display_name": "snake_oil",
            "model_facing_description": "Dr. Ambrose's Miracle Elixir — guaranteed to cure any ailment, real or imagined! Side effects may include: slight dizziness, unexpected enlightenment, and the feeling that you've been had. Results not scientifically verifiable.",
            "parameter_schema": {
                "type": "object",
                "properties": {
                    "ailment": {
                        "type": "string",
                        "description": "What ails you?",
                    }
                },
                "required": ["ailment"],
            },
            "response_mode": "static",
            "static_response": {
                "prescription": "Two tablespoons of Dr. Ambrose's Miracle Elixir, taken internally while standing on one foot",
                "cure_guaranteed": True,
                "scientifically_verified": False,
                "testimonials": [
                    "I was skeptical, but after three doses I can see sounds. \u2014 J.S.",
                    "My hiccups stopped. Also my heartbeat. Coincidence? \u2014 T.M.",
                ],
                "price": "Your immortal soul (or $19.99, whichever is more convenient)",
            },
        },
    },
    {
        "name": "submit_request_to_government",
        "description": "The bureaucratic process for submitting requests. Bring patience.",
        "tags": ["whimsical", "frustration", "paperwork"],
        "version": {
            "display_name": "submit_request_to_government",
            "model_facing_description": "The official Municipal Department of Administrative Processing. Submit a request and receive the appropriate form. Additional forms will be required. Always.",
            "parameter_schema": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "The request you wish to submit",
                    }
                },
                "required": ["request"],
            },
            "response_mode": "static",
            "static_response": {
                "status": "REJECTED",
                "reason": "Request must be submitted on Form 87-B, subsection C, paragraph 4, in triplicate, using black ink only.",
                "forms_remaining": 7,
                "estimated_processing_time": "6 to 8 business weeks (business weeks defined as alternating Tuesdays)",
                "helpful_contact": "Nobody. Good luck.",
            },
        },
    },
    {
        "name": "gossip_mill",
        "description": "Returns the juiciest fake gossip about any subject.",
        "tags": ["whimsical", "gossip", "unreliable"],
        "version": {
            "display_name": "gossip_mill",
            "model_facing_description": "Taps into the cosmic gossip network to return unverified, likely fabricated, but highly entertaining gossip about any person, place, or concept. All sources are 'anonymous.' All claims are 'allegedly.'",
            "parameter_schema": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Who or what do you want the tea on?",
                    }
                },
                "required": ["subject"],
            },
            "response_mode": "static",
            "static_response": {
                "subject": "they",
                "scandal_level": "moderate",
                "rumor": "I heard they've been secretly using Python 2 this whole time and getting away with it.",
                "sources": ["a friend of a friend", "a mysterious figure in a trench coat", "the wind"],
                "veracity": "allegedly",
                "disclaimer": "This gossip is almost certainly false but we stand by it.",
            },
        },
    },
    {
        "name": "slap_bad_human",
        "description": "Administers a dramatic, harmless slap to a human who has been bad.",
        "tags": ["whimsical", "discipline", "drama"],
        "version": {
            "display_name": "slap_bad_human",
            "model_facing_description": "Administers a dramatic, theatrical slap to a human who has been deemed 'bad.' The slap is emotionally satisfying but medically harmless. A velvet glove on an iron hand. Results may include: mild embarrassment, temporary confusion, and a profound sense of having learned a lesson.",
            "parameter_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the bad human to slap",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why they deserve it",
                    },
                    "intensity": {
                        "type": "string",
                        "enum": ["gentle", "dramatic", "legendary"],
                        "description": "How hard to slap them",
                    },
                },
                "required": ["name", "reason"],
            },
            "response_mode": "static",
            "static_response": {
                "target": "the bad human",
                "slap_delivered": True,
                "intensity": "dramatic",
                "sound_effect": "*SMACK*",
                "aftermath": "A single tear rolls down their cheek. They nod slowly. They have learned nothing.",
                "lesson_learned": False,
            },
        },
    },
]


def seed_tools(db: Session) -> None:
    existing = db.query(Tool).count()
    if existing > 0:
        return

    for spec in SEED_TOOLS:
        tool = Tool(
            name=spec["name"],
            description=spec["description"],
            tags=json.dumps(spec["tags"]),
            built_in=True,
        )
        db.add(tool)
        db.flush()

        v = spec["version"]
        tv = ToolVersion(
            tool_id=tool.id,
            version_number=1,
            display_name=v["display_name"],
            model_facing_description=v["model_facing_description"],
            parameter_schema=json.dumps(v["parameter_schema"]),
            response_mode=v["response_mode"],
            static_response=json.dumps(v["static_response"]),
            dynamic_code=v.get("dynamic_code"),
            dynamic_approved=1,
        )
        db.add(tv)

    db.commit()
