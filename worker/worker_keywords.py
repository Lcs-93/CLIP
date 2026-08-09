from __future__ import annotations


COMMERCIAL_KEYWORDS = {
    # Appels à l'action commerciaux
    "code promo", "lien en description", "lien en bio", "cliquez", "clique",
    "abonnez-vous", "abonne-toi", "s'abonner", "abonner", "subscribe",
    "likez", "like", "liker", "partage", "partager",
    "commentez", "commente", "commenter", "notification", "notifications", "cloche",
    "pouce", "pouce bleu", "petit pouce",
    # Sponsoring
    "sponsor", "sponsorisé", "partenaire", "partenariat", "partnership",
    "merci à", "thanks to", "présenté par", "brought to you",
    "accompagner", "accompagne", "nous accompagne",
    # Vente directe
    "achetez", "achète", "acheter", "discount", "réduction", "soldes",
    "offre", "promo", "promotion", "gratuit", "free", "cadeau", "cadeaux",
    "télécharger", "téléchargez", "installer", "installez", "foncez",
    "tirages", "tirage", "obtenir", "obtenez", "recevoir", "recevez",
    "profitez", "profiter", "bénéficiez", "bénéficier",
    # Urgence/Rareté
    "exclusif", "exclusive", "limité", "limitée", "durée limitée",
    "dépêchez", "dépêche", "vite", "rapidement",
    "maintenant", "aujourd'hui", "dernière chance",
    # Jeux mobiles / gacha
    "6 étoiles", "5 étoiles", "4 étoiles", "étoiles",
    "rare", "légendaire", "épique", "mythique",
    "opérateur", "personnage", "perso", "skin",
    "caisse", "caisses", "coffre", "coffres", "lootbox",
    "gemmes", "cristaux", "pièces", "monnaie",
    # Codes et liens
    "utilisez le code", "avec le code", "use code", "mon code",
    "lien affilié", "affiliate", "shop", "boutique", "store",
    "dispo", "disponible",
    # Self-promo
    "mon merch", "merchandise", "mes produits", "ma marque",
    "suivez-moi", "follow me", "instagram", "twitter", "tiktok",
    "ma chaîne", "mon discord", "rejoignez", "join",
    # Plateformes
    "pc", "mobile", "android", "ios", "playstation", "ps5", "ps4", "xbox",
    "app store", "play store", "steam",
}

COMMERCIAL_PHRASES = [
    # Liens et descriptions
    "lien dans la description", "lien dans la bio", "link in bio",
    "link in description", "n'oubliez pas de", "n'oublie pas de",
    "première ligne de description", "en première ligne",
    "le lien qui est présent", "avec le lien",
    "cliquez sur le lien", "clique sur le lien",
    # Likes et abonnements
    "laissez un like", "laisse un like", "laisser un like", "mettez un pouce",
    "activez la cloche", "active la cloche", "hit the bell",
    "smash that like", "drop a like", "leave a comment",
    "pensez à vous abonner", "pense à t'abonner", "pensez-y",
    "ça me fait plaisir", "moi ça me fait plaisir",
    "ça me peine", "ce qui me peine",
    "ça prend quoi", "cinq secondes",
    # Sponsors et partenaires
    "code promo", "promo code", "use my code", "utilisez mon code",
    "merci à notre sponsor", "thanks to our sponsor",
    "cette vidéo est sponsorisée", "this video is sponsored",
    "partenaire de cette vidéo", "qui est le partenaire",
    "merci à eux", "merci de nous accompagner",
    "qui nous accompagne", "qui m'accompagne",
    # Recommandations
    "je vous recommande", "je te recommande",
    "allez voir", "va voir", "check out", "go check",
    "je vous conseille", "je te conseille",
    # Disponibilité et téléchargement
    "disponible maintenant", "available now", "out now",
    "le jeu est disponible", "dispo sur", "disponible sur",
    "télécharger avec le lien", "vous pouvez le télécharger",
    "vous pouvez télécharger", "tu peux télécharger",
    "c'est le moment ou jamais", "c'est le moment",
    # Produits et nouveautés
    "nouveau produit", "new product", "nouvelle collection",
    "tout nouveau", "toute nouvelle", "vient de sortir",
    "pour fêter sa sortie", "grâce aux divers événements",
    # Offres et cadeaux
    "vous allez obtenir", "tu vas obtenir",
    "vous allez recevoir", "tu vas recevoir",
    "tout ça c'est grâce", "et tout ça",
    "tirages gratuits", "tirage gratuit",
    # Transitions pub
    "place à la suite", "sur ce je", "et sur ce",
    "je claque des doigts", "et je claque",
    "je profite", "j'en profite",
    # Descriptions de jeux (souvent = pub)
    "c'est un jeu", "c'est quoi",
    "développé par", "créé par",
    "vous allez incarner", "tu vas incarner",
    "partir à l'aventure", "partez à l'aventure",
    "large panel", "personnages très stylés",
    "cinématiques", "à couper le souffle",
    "vous faire kiffer", "te faire kiffer",
    # Appels à l'action finaux
    "donc voilà foncez", "voilà foncez", "foncez le jeu",
    "le jeu est trop cool", "trop cool",
    "je rappelle", "je vous rappelle",
    "tout est disponible", "tout est dispo",
]

STORY_START_MARKERS = {
    # Introductions d'histoire
    "alors", "donc", "du coup", "en fait", "figure-toi", "figurez-vous",
    "imagine", "imaginez", "écoute", "écoutez", "attends", "attendez",
    "je vais vous raconter", "je vais te raconter", "laissez-moi vous dire",
    "il faut que je vous raconte", "faut que je te raconte",
    "l'autre jour", "hier", "la semaine dernière", "y'a quelques jours",
    "un jour", "une fois", "c'était", "j'étais", "on était",
    # Story hooks anglais
    "so basically", "okay so", "let me tell you", "story time",
}

STORY_CONTINUATION_MARKERS = {
    # Transitions narratives
    "et là", "et puis", "après", "ensuite", "soudain", "tout à coup",
    "mais", "sauf que", "le problème", "le truc", "genre",
    "tu vois", "vous voyez", "bref", "enfin", "quoi",
    "c'est là que", "c'est à ce moment", "et devine", "devinez",
    # Anglais
    "and then", "but then", "so then", "suddenly", "turns out",
}

STORY_CLIMAX_MARKERS = {
    # Pics émotionnels
    "j'te jure", "je vous jure", "sérieux", "franchement",
    "c'était dingue", "c'était fou", "incroyable", "hallucinant",
    "j'en reviens pas", "j'y crois pas", "tu peux pas imaginer",
    "le pire", "le meilleur", "la meilleure partie",
    # Anglais
    "i swear", "no joke", "literally", "the best part", "the worst part",
}

STORY_END_MARKERS = {
    # Conclusions
    "voilà", "et voilà", "bref", "fin de l'histoire", "morale de l'histoire",
    "du coup maintenant", "depuis", "c'est comme ça que",
    "et c'est pour ça", "et c'est pourquoi",
    # Anglais
    "so yeah", "anyway", "that's how", "and that's why", "the end",
}

HOOK_MARKERS = {
    # Questions accrocheuses
    "tu sais quoi", "vous savez quoi", "devinez quoi", "guess what",
    "tu sais pas", "vous savez pas", "tu connais", "vous connaissez",
    # Promesses de valeur
    "je vais vous montrer", "je vais te montrer", "regarde ça",
    "regardez ça", "watch this", "check this",
    "faut que je vous dise", "faut que je te dise",
    "le truc c'est", "le problème c'est", "le pire c'est",
    # Teasers
    "attendez la fin", "attends la fin", "wait for it",
    "vous allez pas croire", "tu vas pas croire",
    "c'est dingue", "c'est fou", "c'est incroyable",
    # Urgence/Curiosité
    "il faut que", "faut absolument", "arrête tout",
    "stop", "attendez", "attends",
}

PUNCHLINE_MARKERS = {
    # Révélations
    "et boom", "et bam", "et là", "plot twist",
    "la chute", "le plot twist", "surprise",
    # Conclusions satisfaisantes
    "et c'est comme ça", "voilà pourquoi", "voilà comment",
    "du coup", "résultat", "conclusion",
    "fin", "the end", "et voilà",
    # Réactions fortes
    "j'en reviens pas", "je suis choqué", "je suis mort",
    "c'était ça", "c'est ça", "exactement",
    "tu vois", "vous voyez",
}

EMOTION_INTENSIFIERS = {
    # Intensité haute
    "vraiment", "tellement", "grave", "trop", "super",
    "méga", "ultra", "hyper", "complètement", "totalement",
    # Jurés/Serments (crédibilité)
    "je te jure", "je vous jure", "j'te jure", "wallah",
    "sur ma vie", "sur la tête de", "i swear",
    # Emphase
    "littéralement", "literally", "genre", "style",
    "carrément", "franchement", "sérieux", "sérieusement",
    # Superlatifs
    "le plus", "la plus", "le pire", "le meilleur",
    "jamais vu", "jamais entendu", "de ma vie",
}

DIALOGUE_MARKERS = {
    # Interactions
    "ah bon", "ah ouais", "ah oui", "c'est vrai",
    "non mais", "mais non", "mais oui", "mais genre",
    "t'es sérieux", "vous êtes sérieux", "are you serious",
    # Réponses vives
    "exactement", "voilà", "c'est ça", "that's it",
    "pas du tout", "absolument pas", "jamais",
    # Questions rhétoriques
    "tu vois ce que je veux dire", "vous voyez",
    "c'est pas dingue ça", "c'est pas fou ça",
}

MID_THOUGHT_MARKERS = {
    "parce que", "because", "car", "puisque", "comme",
    "quand", "when", "lorsque", "alors que", "while",
    "si", "if", "même si", "even if",
    "qui", "que", "which", "that", "dont",
    "mais", "but", "cependant", "however",
    "et", "and", "ou", "or",
    "pour", "for", "afin de", "in order to",
}

FORBIDDEN_END_WORDS = {
    # Verbes auxiliaires / incomplets (français)
    "suis", "es", "est", "sommes", "êtes", "sont",
    "ai", "as", "a", "avons", "avez", "ont",
    "vais", "vas", "va", "allons", "allez", "vont",
    "peux", "peut", "pouvons", "pouvez", "peuvent",
    "dois", "doit", "devons", "devez", "doivent",
    "fais", "fait", "faisons", "faites", "font",
    "veux", "veut", "voulons", "voulez", "veulent",
    "sais", "sait", "savons", "savez", "savent",
    "étais", "était", "étions", "étiez", "étaient",
    "avais", "avait", "avions", "aviez", "avaient",
    "serai", "sera", "serons", "serez", "seront",
    # Verbes auxiliaires (anglais)
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did", "doing",
    "will", "would", "shall", "should", "can", "could", "may", "might",
    # Prépositions (français)
    "de", "du", "des", "à", "au", "aux", "pour", "par",
    "dans", "sur", "sous", "avec", "sans", "chez", "vers",
    "entre", "contre", "depuis", "pendant", "durant",
    # Prépositions (anglais)
    "of", "to", "in", "on", "at", "for", "with", "about",
    "into", "through", "during", "before", "after",
    # Conjonctions/Relatifs (français)
    "que", "qui", "dont", "où", "quoi", "lequel", "laquelle",
    "et", "ou", "mais", "donc", "car", "ni", "si", "comme",
    "parce", "puisque", "lorsque", "quand", "tandis",
    # Conjonctions (anglais)
    "that", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "and", "or", "but", "because", "although", "though", "while", "if",
    # Déterminants (français)
    "le", "la", "les", "un", "une", "mon", "ma", "mes",
    "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos",
    "votre", "vos", "leur", "leurs", "ce", "cette", "ces",
    # Déterminants (anglais)
    "the", "a", "an", "my", "your", "his", "her", "its", "our", "their",
    "this", "that", "these", "those",
    # Négations incomplètes
    "pas", "plus", "jamais", "rien", "personne", "aucun", "aucune",
    "not", "never", "nothing", "nobody", "none",
    # Pronoms incomplets
    "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles",
    "me", "te", "se", "lui", "eux",
    "i", "you", "he", "she", "it", "we", "they",
    # Adverbes de liaison
    "très", "trop", "assez", "vraiment", "bien", "mal",
    "very", "too", "really", "quite", "rather",
}

LAUGHTER_TOKENS = {
    "haha",
    "hahaha",
    "ahah",
    "ahahah",
    "hehe",
    "hehehe",
    "lol",
    "lmao",
    "mdr",
    "ptdr",
    "xptdr",
    "rires",
    "rire",
    "laugh",
    "laughter",
    "giggle",
    "marrant",
    "rigole",
    "rigolo",
}

TAG_KEYWORDS = {
    "drôle": {
        "lol",
        "mdr",
        "ptdr",
        "haha",
        "hahaha",
        "rires",
        "rire",
        "blague",
        "vanne",
        "marrant",
        "rigolo",
        "punchline",
        "funny",
    },
    "surprise": {
        "quoi",
        "hein",
        "attends",
        "wtf",
        "wow",
        "incroyable",
        "serieux",
        "sérieux",
        "choqué",
        "choque",
        "impossible",
        "dingue",
        "nope",
    },
    "tension": {
        "putain",
        "merde",
        "fuck",
        "attention",
        "stress",
        "panique",
        "panic",
        "peur",
        "danger",
        "chaud",
        "tendu",
        "angoisse",
    },
    "action": {
        "action",
        "go",
        "let's",
        "lets",
        "boom",
        "explosion",
        "rush",
        "fight",
        "headshot",
        "kill",
        "frag",
        "gg",
    },
    "émotion": {
        "triste",
        "pleure",
        "larmes",
        "émotion",
        "emotion",
        "touchant",
        "amour",
        "heureux",
        "désolé",
        "desole",
    },
    "révélation": {
        "secret",
        "révélation",
        "revelation",
        "plot",
        "twist",
        "spoiler",
        "vérité",
        "verite",
        "enfait",
    },
}

PHRASE_KEYWORDS = {
    "drôle": ["tu vas rire", "c'est drôle", "j'en peux plus", "je suis mort"],
    "surprise": [
        "no way",
        "oh my god",
        "c'est pas vrai",
        "c'est pas possible",
        "attends",
        "quoi",
    ],
    "tension": ["attention", "ça craint", "c'est chaud", "c'est tendu"],
    "révélation": ["en fait", "en réalité", "la vérité", "plot twist", "spoiler alert"],
    "action": ["let's go", "c'est parti", "go go", "on y va"],
    "émotion": ["ça me touche", "j'ai les larmes", "ça fait mal"],
}
