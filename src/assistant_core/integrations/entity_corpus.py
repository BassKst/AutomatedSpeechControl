class Corpus:
    def __init__(self, name: str, data: dict):
        self.name = name
        self.data = data


class EntityCorpus:
    region = Corpus(
        "region",
        {
            "NL": [
                "нидерландах",
                "голландии",
                "амстердаме",
                "роттердаме",
                "нидеры"
            ],

            "DE": [
                "германии",
                "франкфурте",
                "берлине",
                "немецком сервере",
                "германском узле"
            ],

            "FI": [
                "финляндии",
                "хельсинки",
                "финском сервере"
            ],

            "US": [
                "сша",
                "америке",
                "нью йорке",
                "лос анджелесе",
                "американском сервере"
            ]
        }
    )

    number = Corpus(
        "number",
        {
            "1": [
                "один",
                "первый",
                "первую",
                "раз"
            ],

            "2": [
                "два",
                "второй",
                "вторую"
            ],

            "3": [
                "три",
                "третий",
                "третью"
            ],

            "4": [
                "четыре",
                "четвертый"
            ]
        }
    )

    provider = Corpus(
        "provider",
        {
            "hetzner": [
                "hetzner",
                "хетзнер",
                "хецнер"
            ],

            "ovh": [
                "ovh",
                "овеаш",
                "овх"
            ],

            "digitalocean": [
                "digital ocean",
                "digitalocean",
                "диджитал оушен"
            ]
        }
    )

    vpn_type = Corpus(
        "vpn_type",
        {
            "vless_reality": [
                "reality",
                "vless reality",
                "реалити",
                "реальность"
            ],

            "vless_tls": [
                "tls",
                "vless tls",
                "тлс"
            ],

            "shadowsocks": [
                "shadowsocks",
                "шедоусокс",
                "ss"
            ]
        }
    )

    cpu = Corpus(
        "cpu",
        {
            "2": [
                "двухядерный"
            ],

            "4": [
                "четырехядерный"
            ]
        }
    )

    ram = Corpus(
        "ram",
        {
            "4": [
                "4 гига",
                "4 гб",
                "четыре гига"
            ],

            "8": [
                "8 гигов",
                "8 гб",
                "восемь гигов"
            ]
        }
    )
