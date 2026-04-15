"""
Utilities module
Helper functions used across the app
"""


def rupees_in_words(amount):
    """Convert a number to Indian currency words: Rupees Forty Three Thousand Only"""
    try:
        amount = float(amount)
    except:
        return ""

    if amount <= 0:
        return "Zero Rupees Only"

    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
            "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
            "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty",
            "Sixty", "Seventy", "Eighty", "Ninety"]

    def get_hundreds(n):
        if n == 0:
            return ""
        result = ""
        if n >= 100:
            result += ones[n // 100] + " Hundred "
            n %= 100
        if n >= 20:
            result += tens[n // 10] + " "
            n %= 10
        if n > 0:
            result += ones[n] + " "
        return result.strip()

    int_part = int(amount)
    result = ""

    if int_part >= 10000000:  # Crore
        result += get_hundreds(int_part // 10000000) + " Crore "
        int_part %= 10000000

    if int_part >= 100000:  # Lakh
        result += get_hundreds(int_part // 100000) + " Lakh "
        int_part %= 100000

    if int_part >= 1000:  # Thousand
        result += get_hundreds(int_part // 1000) + " Thousand "
        int_part %= 1000

    if int_part > 0:
        result += get_hundreds(int_part)

    return f"Rupees {result.strip()} Only"
