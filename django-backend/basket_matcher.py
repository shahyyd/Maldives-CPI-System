import os
import re
import django
from difflib import SequenceMatcher

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpi_admin.settings")
django.setup()

from cpi.models import CpiBasket, CpiMethodology


METHODOLOGY_CODE = "CPI2022"


class BasketMatcher:

    def __init__(self):
        self.methodology = CpiMethodology.objects.get(methodology_code=METHODOLOGY_CODE)

        self.basket_items = list(
            CpiBasket.objects.filter(
                methodology=self.methodology,
                is_basket_item=True,
                is_active=True
            )
        )

    def clean_text(self, text):
        if not text:
            return ""

        text = str(text).lower().strip()
        text = text.replace("&", " and ")
        text = re.sub(r"\(.*?\)", "", text)
        text = text.replace("/", " ")
        text = text.replace("-", " ")

        if "," in text:
            text = text.split(",")[0]

        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def similarity(self, a, b):
        return SequenceMatcher(
            None,
            self.clean_text(a),
            self.clean_text(b)
        ).ratio()

    def find_basket(self, product_name, product_specification=None, excel_subgroup=None):

        product_clean = self.clean_text(product_name)
        specification_clean = self.clean_text(product_specification)
        subgroup_clean = self.clean_text(excel_subgroup)

        # Rule 1 - Exact product name
        for basket in self.basket_items:
            basket_name = self.clean_text(basket.basket_item_name)

            if product_clean == basket_name:
                return {
                    "basket": basket,
                    "basket_id": basket.basket_id,
                    "basket_code": basket.basket_code,
                    "basket_name": basket.basket_item_name,
                    "confidence": 100,
                    "match_type": "Exact Product Name"
                }

        # Rule 2 - Synonyms
        synonyms = {
            "hand wash": "hand wash liquid",
            "face wash": "facial cleanser",
            "paratha": "paratha",
            "tooth paste": "toothpaste",
            "shampoo": "shampoo",
        }

        product_synonym = synonyms.get(product_clean)

        if product_synonym:
            synonym_clean = self.clean_text(product_synonym)

            for basket in self.basket_items:
                basket_name = self.clean_text(basket.basket_item_name)

                if synonym_clean == basket_name:
                    return {
                        "basket": basket,
                        "basket_id": basket.basket_id,
                        "basket_code": basket.basket_code,
                        "basket_name": basket.basket_item_name,
                        "confidence": 98,
                        "match_type": "Normalized Synonym"
                    }

        # Rule 3 - Exact product specification
        if specification_clean:
            for basket in self.basket_items:
                basket_name = self.clean_text(basket.basket_item_name)

                if specification_clean == basket_name:
                    return {
                        "basket": basket,
                        "basket_id": basket.basket_id,
                        "basket_code": basket.basket_code,
                        "basket_name": basket.basket_item_name,
                        "confidence": 96,
                        "match_type": "Exact Product Specification"
                    }

        # Rule 4 - Subgroup assisted exact match
        if subgroup_clean:
            for basket in self.basket_items:
                basket_name = self.clean_text(basket.basket_item_name)
                basket_parent = self.clean_text(getattr(basket.parent, "basket_item_name", ""))

                if product_clean == basket_name and subgroup_clean in basket_parent:
                    return {
                        "basket": basket,
                        "basket_id": basket.basket_id,
                        "basket_code": basket.basket_code,
                        "basket_name": basket.basket_item_name,
                        "confidence": 94,
                        "match_type": "Subgroup Assisted Exact Match"
                    }

        # Rule 5 - Product contains all basket words
        best_match = None
        best_word_count = 0

        product_words = set(product_clean.split())

        for basket in self.basket_items:
            basket_name = self.clean_text(basket.basket_item_name)
            basket_words = set(basket_name.split())

            if basket_words and basket_words.issubset(product_words):
                if len(basket_words) > best_word_count:
                    best_word_count = len(basket_words)
                    best_match = basket

        if best_match:
            return {
                "basket": best_match,
                "basket_id": best_match.basket_id,
                "basket_code": best_match.basket_code,
                "basket_name": best_match.basket_item_name,
                "confidence": 90,
                "match_type": "Basket Words Contained"
            }

        # Rule 6 - Fuzzy match
        best_match = None
        best_score = 0

        for basket in self.basket_items:
            score = self.similarity(product_clean, basket.basket_item_name)

            if score > best_score:
                best_score = score
                best_match = basket

        if best_match and best_score >= 0.60:
            return {
                "basket": best_match,
                "basket_id": best_match.basket_id,
                "basket_code": best_match.basket_code,
                "basket_name": best_match.basket_item_name,
                "confidence": round(best_score * 100),
                "match_type": "Fuzzy Match"
            }

        return None