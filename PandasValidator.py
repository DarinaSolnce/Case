import pandas as pd
import phonenumbers
import requests
import numpy as np
import re

# Валидация Телефона
from phonenumbers import NumberParseException


class PhoneValidator:

    def validate(self, phone):
        x = None
        try:
            x = phonenumbers.parse(phone, "RU")
        except NumberParseException:
            return None
        if not phonenumbers.is_possible_number(x) or not phonenumbers.is_valid_number(x):
            return None
        return phonenumbers.format_number(x, phonenumbers.PhoneNumberFormat.E164)


# Валидация E-mail
class EmailValidator:

    def validate_part(self, part, symbols):
        regexp = '^[A-z0-9' + symbols + ']+$'
        prog = re.compile(regexp)
        if not prog.match(part):
            return False
        if "" == part:
            return False
        if len(part) > 63:
            return False
        if part.startswith(".") or part.endswith(".") or part.startswith("-") or part.endswith("-"):
            return False
        return True

    def validate_domain_part(self, part):
        is_part_valid = self.validate_part(part, "\-\.")
        if not is_part_valid:
            return False
        if part[0].isdigit() or part[-1].isdigit():
            return False
        return True

    def validate_email(self, email):
        array_email = email.split("@")
        if len(array_email) != 2:
            return None
        else:
            first_part = array_email[0]
            if ".." in first_part:
                return None
            is_first_part_valid = self.validate_part(first_part, "\^\-\._!#$%&'*+/=?~`}{|")
            if not is_first_part_valid:
                return None
            second_part = array_email[1]
            new_array = second_part.split(".")
            if len(new_array) != 2:
                return None
            else:
                is_second_part_valid = self.validate_domain_part(new_array[0])
                is_third_part_valid = self.validate_domain_part(new_array[1])
                if not is_second_part_valid or not is_third_part_valid:
                    return None
        return email

# Валидация Городов


BASE_URL = "https://api.hh.ru/areas"
s = requests.Session()
response = s.get(BASE_URL)
content = s.get(BASE_URL).json()
# print(json.dumps(content, sort_keys=False, ensure_ascii=False, indent=2))
d = {}


def flat_cities(contents):
    # выход из рекурсии
    d[contents["name"]] = contents["id"]
    if len(contents["areas"]) > 0:
        for item in contents["areas"]:
            flat_cities(item)


for cont in content:
    flat_cities(cont)


class CityValidator:
    d = {}

    def __init__(self, d):
        self.d = d
        self.cities = list(self.d.keys())

    def validate_part(self, part):
        regexp2 = '^[А-Яа-я\-]+$'
        prog2 = re.compile(regexp2)
        if prog2.match(part):
            regexp = '^(|пгт|пос|р?п|г|с|д|обл|кр|мкр|станица|раион|р-н|область|краи|республика|респуб|ао)$'
            prog = re.compile(regexp)
            return not prog.match(part)
        return False

    def validate(self, city):
        new_city = city.replace("й", "и").replace("ё", "е").strip(" ")
        parts_city = re.split(" |\. |, ", new_city)
        new_mass = []
        for i in parts_city:
            if self.validate_part(i):
                new_mass.append(i)
        if len(new_mass) == 0:
            return None
        return " ".join(new_mass)

    def find(self, city):
        validate_city = self.validate(city)
        if validate_city is None:
            return None
        if validate_city in self.cities:
            return d[validate_city]
        else:
            min_distance = self.get_distance(self.cities[0], validate_city)
            found = self.cities[0]
            for i in self.cities:
                dist = self.get_distance(i, validate_city)
                if dist < min_distance:
                    min_distance = dist
                    found = i
                if dist == 1:
                    break
        return d[found]

    # param: a - то, к чему нужно привести b
    # "Calculates the Levenshtein distance between a and b."

    def get_distance(self, a, b):
        n, m = len(a), len(b)
        if n > m:
            # Make sure n <= m, to use O(min(n,m)) space
            a, b = b, a
            n, m = m, n

        current_row = range(n + 1)  # Keep current and previous row, not entire matrix
        for i in range(1, m + 1):
            previous_row = current_row
            current_row = [i] + [0] * n
            for j in range(1, n + 1):
                add = previous_row[j] + 1
                delete = current_row[j - 1] + 1
                change = previous_row[j - 1]
                if a[j - 1] != b[i - 1]:
                    change += 1
                current_row[j] = min(add, delete, change)

        return current_row[n]


city_validators = CityValidator(d)
city_validators.find("г. Москва")

# Pandas

crm = pd.read_csv("CRM_sample.tsv", sep='\t')
filtered_crm = crm[crm["City"].notnull() & (crm["Email"].notnull() | crm["HomePhone"].notnull())]
crm_email = filtered_crm["Email"]
crm_phone = filtered_crm["HomePhone"]
crm_city = filtered_crm["City"]


def check(email):
    email_validator = EmailValidator()
    result = []
    for i in email:
        if i is not np.nan:
            result.append(email_validator.validate_email(i))
        else:
            result.append(i)
    return result


def check_phone(crm_phones):
    phone_valid = PhoneValidator()
    list_phones = []
    for j in crm_phones:
        if j is not np.nan:
            list_phones.append(phone_valid.validate(j))
        else:
            list_phones.append(j)
    return list_phones


def check_city(city_crm):
    validator = CityValidator(d)
    result = []
    for k in city_crm:
        result.append(validator.find(k))
    return result


temp_list = check(crm_email)
filtered_crm = filtered_crm.assign(valid_email=temp_list)

temp_list_phone = check_phone(crm_phone)
filtered_crm = filtered_crm.assign(valid_phone=temp_list_phone)

temp_list_city = check_city(crm_city)
filtered_crm = filtered_crm.assign(id_city=temp_list_city)


offers = pd.read_csv("offers.tsv", sep='\t')
offers.head()
filtered_offers = offers[(offers["Place"].notnull() | offers["Country"].notnull()) & offers["Text"].notnull()]
temp_list_city = check_city(filtered_offers["Place"])
filtered_offers = filtered_offers.assign(id_city=temp_list_city)
filtred_crm = filtered_crm.merge(filtered_offers, on="id_city", how="inner").loc[:, ["FirstName", "LastName", "Place", "valid_email", "valid_phone", "Text"]]
filtered_offers_2 = filtred_crm[(filtred_crm["valid_email"].notnull() | filtred_crm["valid_phone"].notnull())]
print(filtered_offers_2)