"""Fake-friend reply generator.

Every drink you "text" gets a reply that should read like a normal thread with a
26-year-old guy: mostly lowercase, short reactions mixed with longer rambles about
work / gym / sports / food / dating / plans, sometimes split across two or three
bubbles, sometimes ending in a question. Nothing in the text carries the BAC any
more; the app reveals that on tap instead.

generate_reply() returns a list of bubble strings.
"""
import random
from datetime import datetime, timedelta, timezone

GREETINGS = [
    "yooo", "ayy what's good", "wassup man", "yo", "lol hey", "what's up dude",
    "oh hey lol", "ayyy", "sup", "yo yo", "well well well look who it is",
    "there he is", "yooo what's good", "lol hi", "my guy",
]

SHORT = [
    "lol", "lmao", "haha", "bet", "yessir", "say less", "word", "fr", "nice", "ayy",
    "hell yeah", "lol ok", "W", "big W", "love that", "oh nice", "lmaooo", "solid",
    "respect", "good call", "fair", "true", "lol same", "no shot", "deadass?", "sheesh",
    "let's gooo", "ok ok", "yup", "haha nice", "lol classic", "hahaha", "bro", "dude",
    "yessss", "ha", "huge", "goated", "k", "oh word", "copy", "lmao ok", "that's the move",
    "lol i see you", "okayyy", "based", "nice nice", "lol valid", "oh for sure", "100%",
    "facts", "haha yes", "ok bet", "lol yeah", "yeah lol", "ayo", "wild", "lmao what",
    "ok that's fair", "stop lol", "lol noted", "say no more", "good man", "proud of you",
]

MED = [
    "lol ok that's actually a good call",
    "bro you're unhinged for that",
    "i mean fair enough honestly",
    "haha ok i respect it",
    "lmao why am i not surprised",
    "ok that's a solid choice ngl",
    "yeah that tracks lol",
    "lol you're committed i'll give you that",
    "ok ok i see you",
    "classic you honestly",
    "lol i'd expect nothing less",
    "honestly same, rough week",
    "lmao i'm so jealous rn",
    "ok save me one",
    "where you at rn",
    "who's all there",
    "lol tell everyone i said hi",
    "haha i'll be there in like 20",
    "lmao i'm still at work kill me",
    "wait who are you with",
    "bro send pics lol",
    "lol is it good",
    "ok that's fire",
    "haha ok you're having a night",
    "lol i just got home, might come through",
    "nah i'm good tonight, got an early thing tmrw",
    "lmao i literally just said that to kyle",
    "ok i'm actually down for that this weekend",
    "bro i'm so tired idk how you do it",
    "lol my body would simply not allow that rn",
    "haha ok enjoy, i'm couch locked",
    "yeah i'm about to do the same tbh",
    "lmao text me when you leave",
    "ok but did you eat anything first",
    "lol respectfully you're a menace",
    "that's a tuesday move if i've ever seen one",
    "ok that's actually my favorite",
    "hahaha i can't with you",
    "you're built different man",
    "lol ok i'm a little jealous",
    "haha ok good, you deserve it after this week",
    "bro you were literally dying yesterday lol",
    "lmao ok hydrate though",
    "good, you needed that",
    "ok that's the one",
    "lol where's this at",
    "haha nice, how is it",
    "yeah same spot as last time?",
]

LIFE = [
    "dude i've been in meetings since 8 and i've accomplished nothing",
    "my boss just scheduled a 4:30 friday meeting. straight to jail",
    "finally hit 225 on bench today lol took me long enough",
    "leg day destroyed me, walking down stairs sideways rn",
    "did you see the end of that game last night?? we got robbed",
    "my fantasy team is cooked, my rb went down in the first quarter",
    "just ate chipotle for the 4th time this week. no regrets",
    "that place by my apt has 75 cent wings on tuesdays we gotta go",
    "the hinge date was fine. she had a cat named greg. idk how i feel",
    "she texted back after 3 days like nothing happened lol",
    "my roommate left dishes in the sink for a week. we're at war",
    "rent went up $150 lmao love that for me",
    "car's making a noise again. pretending i can't hear it",
    "vegas is officially booked btw. clear your calendar",
    "tyler's bachelor party is gonna be a problem",
    "i'm at my 3rd wedding this summer. i need a break",
    "played 2k til 2am and now i'm paying for it",
    "started that new season everyone's talking about, 2 eps in, it's ok so far",
    "my mom asked if i'm 'eating vegetables' again. i'm 26 lol",
    "costco run turned into $240 somehow",
    "golf saturday? 8:40 tee time, i can drive",
    "i've had the same unread email from hr for 3 days and i'm scared to open it",
    "lowkey thinking about getting a dog. talk me out of it",
    "the new coffee place by the office is actually elite",
    "slept through 3 alarms today. not my finest work",
    "tried to cook salmon. apartment smells like a dock now",
    "my watch says i walked 400 steps today lol",
    "does your landlord fix anything or is mine just special",
    "nick is tryna do a lake weekend in august, you in?",
    "my uber driver just gave me unprompted life advice for 20 min",
    "i need to stop doordashing. $31 for a burrito bowl is criminal",
    "our guys are gonna break my heart again aren't they",
    "just found out my coworker makes 15k more than me doing the same job. cool cool cool",
    "the gym was packed, had to wait 10 min for a squat rack like an animal",
    "my sister's making me go to a 'paint and sip' thing saturday. pray for me",
    "ok i finally fixed my sleep schedule and i feel like a new man",
    "got the apartment approved!! moving the 1st, you're helping obviously",
    "the dentist said i grind my teeth. no idea why, totally relaxed person",
    "i left my airpods in the uber again. third pair this year",
    "matt's girlfriend wants to do a group costume for halloween. i'm out",
    "we're doing fantasy draft at jake's on the 24th btw, don't flake",
    "my dad texted me 'call me' with no context and i've aged 10 years",
    "just saw a guy on the train eating a whole rotisserie chicken. no plate. legend",
    "my phone battery is at 4% and i'm 40 min from home. living on the edge",
    "the ac broke in my apartment and it's 84 degrees inside. i'm melting",
    "booked a flight home for thanksgiving, mom already sent a 14 item to-do list",
    "went to the farmers market like an adult and bought nothing but a cookie",
    "my fantasy opponent has 3 guys on bye and is still beating me lol",
    "the barber messed up my fade. hats for 2 weeks",
    "just got passed by a 70 year old on my run. humbling",
    "work laptop updated for 45 min this morning. productivity: zero",
    "ok i signed up for a 10k with brandon and i'm already regretting it",
    "my credit card bill came and i audibly gasped",
    "found a $20 in my jacket pocket, the universe is healing",
    "roommate's girlfriend basically lives here now and she's never bought toilet paper once",
    "trying this new meal prep thing. day 1 and i already hate chicken",
    "the concert tickets went on sale and sold out in 4 min. scalpers are evil",
    "watched a 2 hour youtube video on how submarines work instead of sleeping",
    "i need new tires and i'd rather just not have a car",
    "got a parking ticket in front of my own apartment lol",
    "my grandma friended me on facebook and liked 40 posts from 2015",
    "we should do a trip before everyone gets married and disappears",
    "coach at the gym called me 'big guy' and i don't know if it was a compliment",
    "my neighbor is learning drums. at 11pm. on a wednesday",
    "did a 3 hour nap and woke up not knowing what year it is",
    "i've been staring at this spreadsheet so long the numbers are moving",
    "tried a hot yoga class with my sister. nearly passed out. never again",
    "my ex just got engaged lol. anyway how's your week",
    "put air in my tires and felt like a mechanic",
    "the group chat has 212 unread messages i'm not opening that",
    "kyle wants to go to the casino friday. i give him 40 min before he's broke",
    "i told my boss i'd 'circle back' and i have no intention of circling",
    "cleaned my whole apartment and found a fork under the couch. a fork",
    "the game is on at 7, i got the big screen if you wanna come through",
    "ordered a medium pizza 'for the week'. it did not last the week",
    "trying to decide if $90 for a jersey is reasonable. it's not. i'm buying it",
    "my hinge match's first message was 'what's your rising sign'. ok",
    "lol my mom just texted 'is this still your number' after we talked yesterday",
]

QUESTIONS = [
    "you around this weekend?", "what time you thinking tmrw?", "we still on for sunday?",
    "did you end up calling that guy about the tickets?", "you watching the game later?",
    "wya", "what's the move tonight", "how was the date", "did you talk to your boss yet",
    "you good? haven't heard from you in a min", "lunch this week?", "you still have my charger?",
    "when are you back in town", "did you see the group chat lol", "you free thursday?",
    "hbu", "how's your week going", "ready for this weekend?", "what are you doing for the 4th",
    "you going to matt's thing saturday?", "did you ever hear back about that job",
    "gym tmrw morning or nah", "you want in on the fantasy league this year?",
    "how's the new place", "you eat yet?", "what time does it start", "you driving or ubering",
    "can i borrow your cooler this weekend", "did your car thing get fixed",
    "we doing golf sunday or is it gonna rain", "what are you getting your mom for her bday",
    "you still coming to the lake thing?", "how'd the interview go??", "is tyler coming?",
    "yo did you get the venmo", "wait what are you doing rn", "who you with",
]

# contextual openers, picked by the local time of the drink
CTX_MORNING = [
    "lol it's not even noon", "day drinking i respect it", "bro it's like 11am lol",
    "starting early i see", "lmao a morning man", "it's a brunch kind of day huh",
]
CTX_LATE = [
    "bro go to bed lol", "it's 1am what are you doing", "lol you're still up??",
    "we're still going? respect", "lmao the night is young apparently",
    "ok night owl",
]
CTX_WEEKNIGHT = [
    "bro it's a tuesday", "on a weeknight?? respect", "lol it's a school night",
    "midweek move, i respect it", "lmao it's wednesday bro", "weeknight warrior",
]
CTX_WEEKEND = [
    "lol saturday things", "weekend mode activated", "as you should, it's the weekend",
    "lol friday finally", "weekend vibes", "earned it this week honestly",
]
CTX_MANY = [
    "ok you're having a night lol", "pace yourself champ lol", "lmao who are you tonight",
    "ok slow down there lol", "lol you're on one tonight", "bro lol",
    "haha ok you're officially out out", "lol ok bender",
]
CTX_LOTS = [
    "ok maybe water next lol", "you good? lol", "lol drink some water man",
    "ok ok that's a lot of texts from you tonight lol", "lmao you're gonna feel that tmrw",
    "text me when you get home", "lol get an uber please",
]

EMOJI_TAIL = ["😂", "💀", "🙏", "👀", "😭", "🤝", "🫡"]


def _pick(pool, avoid):
    choices = [p for p in pool if p not in avoid]
    return random.choice(choices or pool)


def _context_opener(local_dt, drink_number):
    """Maybe return a time/count-aware opener, else None."""
    pools = []
    if drink_number >= 8:
        pools.append((CTX_LOTS, 0.35))
    elif drink_number >= 5:
        pools.append((CTX_MANY, 0.22))
    hour = local_dt.hour
    if hour < 12 and hour >= 6:
        pools.append((CTX_MORNING, 0.35))
    elif hour < 5:
        pools.append((CTX_LATE, 0.35))
    elif local_dt.weekday() <= 3 and hour >= 18:
        pools.append((CTX_WEEKNIGHT, 0.15))
    elif local_dt.weekday() >= 4 and hour >= 16:
        pools.append((CTX_WEEKEND, 0.10))
    random.shuffle(pools)
    for pool, p in pools:
        if random.random() < p:
            return random.choice(pool)
    return None


def generate_reply(ts_ms, tz_offset_min=0, drink_number=1, recent=()):
    """Build 1-3 bubbles for the drink logged at ts_ms.

    tz_offset_min follows JS Date.getTimezoneOffset() (minutes to add to local time
    to reach UTC), drink_number is this drink's 1-based index within its session, and
    recent is an iterable of bubble strings already used in the session (so the
    "friend" doesn't repeat himself).
    """
    avoid = set(recent)
    local_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) - timedelta(minutes=tz_offset_min)
    bubbles = []

    if drink_number == 1 and random.random() < 0.7:
        bubbles.append(_pick(GREETINGS, avoid))
        r = random.random()
        if r < 0.45:
            bubbles.append(_pick(QUESTIONS, avoid))
        elif r < 0.65:
            bubbles.append(_pick(LIFE, avoid))
    else:
        ctx = _context_opener(local_dt, drink_number)
        if ctx and ctx not in avoid:
            bubbles.append(ctx)
            r = random.random()
            if r < 0.35:
                bubbles.append(_pick(LIFE, avoid))
            elif r < 0.55:
                bubbles.append(_pick(QUESTIONS, avoid))
        else:
            r = random.random()
            if r < 0.30:
                bubbles = [_pick(SHORT, avoid)]
            elif r < 0.55:
                bubbles = [_pick(MED, avoid)]
            elif r < 0.75:
                bubbles = [_pick(SHORT, avoid), _pick(LIFE, avoid)]
                if random.random() < 0.3:
                    bubbles.append(_pick(QUESTIONS, avoid))
            elif r < 0.90:
                bubbles = [_pick(LIFE, avoid)]
                if random.random() < 0.6:
                    bubbles.append(_pick(QUESTIONS, avoid))
            else:
                bubbles = [_pick(MED, avoid)]
                if random.random() < 0.4:
                    bubbles.append(_pick(LIFE, avoid))
                bubbles.append(_pick(QUESTIONS, avoid))

    out = []
    for b in bubbles:
        if random.random() < 0.08 and not any(b.endswith(e) for e in EMOJI_TAIL):
            b = b + " " + random.choice(EMOJI_TAIL)
        out.append(b)
    return out


# names a new thread gets by default, so the list reads like a contacts list
FRIEND_NAMES = [
    "Jake", "Tyler", "Matt", "Connor", "Ryan", "Brandon", "Kyle", "Nick", "Zach", "Austin",
    "Cole", "Derek", "Evan", "Trevor", "Logan", "Mason", "Brett", "Chase", "Drew", "Garrett",
    "Luke", "Josh", "Danny", "Sam", "Alex", "Ben", "Will", "Jack", "Tommy", "Mike",
]


def suggest_name(taken):
    taken = {t.strip().lower() for t in taken}
    free = [n for n in FRIEND_NAMES if n.lower() not in taken]
    return random.choice(free or FRIEND_NAMES)
