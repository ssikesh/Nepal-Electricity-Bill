from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


# ==========================================================
# NEA DOMESTIC TARIFF
# ==========================================================

TARIFF = {
    5: {
        "minimum": {
            20: 30,
            30: 50,
            50: 50,
            150: 75,
            250: 100,
            float("inf"): 150
        },
        "rates": {
            "0_20": 3.00,
            "21_30": 6.50,
            "31_50": 8.00,
            "51_150": 9.50,
            "151_250": 9.50,
            "251_plus": 11.00
        }
    },

    15: {
        "minimum": {
            20: 50,
            30: 75,
            50: 75,
            150: 100,
            250: 125,
            float("inf"): 175
        },
        "rates": {
            "0_20": 4.00,
            "21_30": 6.50,
            "31_50": 8.00,
            "51_150": 9.50,
            "151_250": 9.50,
            "251_plus": 11.00
        }
    },

    30: {
        "minimum": {
            20: 75,
            30: 100,
            50: 100,
            150: 125,
            250: 150,
            float("inf"): 200
        },
        "rates": {
            "0_20": 5.00,
            "21_30": 6.50,
            "31_50": 8.00,
            "51_150": 9.50,
            "151_250": 9.50,
            "251_plus": 11.00
        }
    },

    60: {
        "minimum": {
            20: 125,
            30: 125,
            50: 125,
            150: 150,
            250: 200,
            float("inf"): 250
        },
        "rates": {
            "0_20": 6.00,
            "21_30": 6.50,
            "31_50": 8.00,
            "51_150": 9.50,
            "151_250": 9.50,
            "251_plus": 11.00
        }
    }
}


# ==========================================================
# CALCULATE BILL
# ==========================================================

def calculate_bill(units, ampere):

    tariff = TARIFF[ampere]

    rates = tariff["rates"]

    # ------------------------------------------------------
    # Minimum fee
    # ------------------------------------------------------

    minimum_fee = 0

    for limit, fee in tariff["minimum"].items():

        if units <= limit:
            minimum_fee = fee
            break

    # ------------------------------------------------------
    # Energy charges
    # ------------------------------------------------------

    breakdown = []

    energy_charge = 0

    # 5A special rule
    # ------------------------------------------------------

    if ampere == 5 and units <= 20:

        energy_charge = 0

        breakdown.append({
            "label": "First 20 units",
            "units": units,
            "rate": 0,
            "amount": 0,
            "free": True
        })

    else:

        # First 20 units
        if units > 0:

            first = min(units, 20)

            amount = first * rates["0_20"]

            energy_charge += amount

            breakdown.append({
                "label": f"First {first:g} units",
                "units": first,
                "rate": rates["0_20"],
                "amount": amount,
                "free": False
            })

        # 21-30
        if units > 20:

            slab_units = min(units - 20, 10)

            amount = slab_units * rates["21_30"]

            energy_charge += amount

            breakdown.append({
                "label": f"Next {slab_units:g} units (21-30)",
                "units": slab_units,
                "rate": rates["21_30"],
                "amount": amount,
                "free": False
            })

        # 31-50
        if units > 30:

            slab_units = min(units - 30, 20)

            amount = slab_units * rates["31_50"]

            energy_charge += amount

            breakdown.append({
                "label": f"Next {slab_units:g} units (31-50)",
                "units": slab_units,
                "rate": rates["31_50"],
                "amount": amount,
                "free": False
            })

        # 51-150
        if units > 50:

            slab_units = min(units - 50, 100)

            amount = slab_units * rates["51_150"]

            energy_charge += amount

            breakdown.append({
                "label": f"Next {slab_units:g} units (51-150)",
                "units": slab_units,
                "rate": rates["51_150"],
                "amount": amount,
                "free": False
            })

        # 151-250
        if units > 150:

            slab_units = min(units - 150, 100)

            amount = slab_units * rates["151_250"]

            energy_charge += amount

            breakdown.append({
                "label": f"Next {slab_units:g} units (151-250)",
                "units": slab_units,
                "rate": rates["151_250"],
                "amount": amount,
                "free": False
            })

        # 251+
        if units > 250:

            slab_units = units - 250

            amount = slab_units * rates["251_plus"]

            energy_charge += amount

            breakdown.append({
                "label": f"Remaining {slab_units:g} units (251+)",
                "units": slab_units,
                "rate": rates["251_plus"],
                "amount": amount,
                "free": False
            })

    # ------------------------------------------------------
    # VAT
    # ------------------------------------------------------

    if units <= 50:

        vat = 0
        taxable_amount = 0

    else:

        # Energy charge belonging to units ABOVE 50
        energy_above_50 = 0

        if units > 50:

            energy_above_50 = min(units - 50, 100) * rates["51_150"]

        if units > 150:

            energy_above_50 += min(units - 150, 100) * rates["151_250"]

        if units > 250:

            energy_above_50 += (units - 250) * rates["251_plus"]

        taxable_amount = minimum_fee + energy_above_50

        vat = taxable_amount * 0.05

    # ------------------------------------------------------
    # Subtotal
    # ------------------------------------------------------

    subtotal = minimum_fee + energy_charge

    before_discount = subtotal + vat

    # ------------------------------------------------------
    # Early payment discount
    # ------------------------------------------------------

    early_discount = before_discount * 0.02

    after_discount = before_discount - early_discount

    return {
        "ampere": ampere,
        "units": units,

        "minimum_fee": minimum_fee,

        "energy_charge": energy_charge,

        "breakdown": breakdown,

        "taxable_amount": taxable_amount,

        "vat": vat,

        "subtotal": subtotal,

        "before_discount": before_discount,

        "early_discount": early_discount,

        "after_discount": after_discount
    }


# ==========================================================
# MAIN PAGE
# ==========================================================

@app.route("/")
def home():

    return render_template("index.html")


# ==========================================================
# API
# ==========================================================

@app.route("/calculate", methods=["POST"])
def calculate():

    data = request.get_json()

    try:

        units = float(data.get("units", 0))

        ampere = int(data.get("ampere", 5))

        if units < 0:

            return jsonify({
                "error": "Units cannot be negative."
            }), 400

        if ampere not in TARIFF:

            return jsonify({
                "error": "Invalid ampere rating."
            }), 400

        result = calculate_bill(
            units,
            ampere
        )

        return jsonify(result)

    except (ValueError, TypeError):

        return jsonify({
            "error": "Invalid input."
        }), 400


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )