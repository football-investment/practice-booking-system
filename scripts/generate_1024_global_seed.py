#!/usr/bin/env python3
"""
Generator: 1024 Global Production Players Seed

Produces: tests/playwright/fixtures/seed_1024_global_players.json

Compatible with: scripts/seed_from_json.py  (import via --fixture=seed_1024_global_players)
Also compatible with: POST /admin/batch-create-players  (API bulk endpoint)

Distribution: 1024 players across 54 countries, 5 regions
  EU:           ~300  (19 countries)
  LATAM:        ~200  (12 countries)
  North America: ~100  (2 countries)
  Africa:        ~200  (11 countries)
  Asia/Pacific:  ~224  (10 countries)

Fields per player (all populated — no nulls on production-required fields):
  email, password, role, name, first_name, last_name,
  date_of_birth, phone, nationality, gender, position,
  specialization, onboarding_completed, payment_verified,
  credit_balance, address (street, city, postal_code, country),
  licenses[LFA_FOOTBALL_PLAYER]

Email format: {first}.{last}.{cc}{idx:03d}@lfa-seed.hu
  - Deterministic, unique, sortable
  - cc = ISO-3166-1 alpha-2 lowercase country code

Usage:
    python scripts/generate_1024_global_seed.py
    → writes tests/playwright/fixtures/seed_1024_global_players.json

Then import:
    DATABASE_URL="..." python scripts/seed_from_json.py --fixture=seed_1024_global_players

Or via API (players array only):
    curl -X POST .../admin/batch-create-players -d @seed_1024_global_players_api.json
"""

import json
import hashlib
import random
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Country data: (name, iso2, phone_prefix, postal_example, cities, streets)
# ---------------------------------------------------------------------------
# Each entry: (country_name, iso2_code, phone_prefix, postal_fmt, [cities], [street_names])
COUNTRIES: List[Tuple] = [
    # ── EU ──────────────────────────────────────────────────────────────────
    ("German",       "de", "+49",  "10117", ["Berlin", "Munich", "Hamburg", "Cologne"],
     ["Hauptstraße", "Berliner Str.", "Schillerstraße", "Bahnhofstr."]),
    ("French",       "fr", "+33",  "75001", ["Paris", "Lyon", "Marseille", "Bordeaux"],
     ["Rue de Rivoli", "Avenue Montaigne", "Rue Lafayette", "Bd Haussmann"]),
    ("Spanish",      "es", "+34",  "28001", ["Madrid", "Barcelona", "Seville", "Valencia"],
     ["Calle Mayor", "Gran Vía", "Paseo de Gracia", "Calle Serrano"]),
    ("Italian",      "it", "+39",  "00100", ["Rome", "Milan", "Naples", "Turin"],
     ["Via Roma", "Via Nazionale", "Corso Italia", "Via Veneto"]),
    ("Dutch",        "nl", "+31",  "1011",  ["Amsterdam", "Rotterdam", "Utrecht", "Eindhoven"],
     ["Keizersgracht", "Herengracht", "Damrak", "Kalverstraat"]),
    ("Portuguese",   "pt", "+351", "1000",  ["Lisbon", "Porto", "Braga", "Coimbra"],
     ["Rua Augusta", "Avenida Liberdade", "Rua do Ouro", "Praça Comércio"]),
    ("Belgian",      "be", "+32",  "1000",  ["Brussels", "Antwerp", "Ghent", "Bruges"],
     ["Rue Neuve", "Meir", "Grote Markt", "Avenue Louise"]),
    ("Polish",       "pl", "+48",  "00-001",["Warsaw", "Krakow", "Wroclaw", "Gdansk"],
     ["Ulica Nowy Świat", "Krakowskie Przedmieście", "Marszałkowska", "Floriańska"]),
    ("Czech",        "cz", "+420", "110 00",["Prague", "Brno", "Ostrava", "Plzen"],
     ["Václavské náměstí", "Na Příkopě", "Wenceslas Sq.", "Náměstí Míru"]),
    ("Hungarian",    "hu", "+36",  "1011",  ["Budapest", "Debrecen", "Pécs", "Miskolc"],
     ["Andrássy út", "Váci utca", "Rákóczi út", "Bajcsy-Zsilinszky út"]),
    ("Romanian",     "ro", "+40",  "010001",["Bucharest", "Cluj-Napoca", "Timisoara", "Iași"],
     ["Calea Victoriei", "Bulevardul Unirii", "Strada Lipscani", "Calea Dorobanților"]),
    ("Croatian",     "hr", "+385", "10000", ["Zagreb", "Split", "Rijeka", "Osijek"],
     ["Ilica", "Trg bana Jelačića", "Vukovarska ulica", "Bogovićeva"]),
    ("Swedish",      "se", "+46",  "111 22",["Stockholm", "Gothenburg", "Malmö", "Uppsala"],
     ["Drottninggatan", "Kungsgatan", "Strandvägen", "Götgatan"]),
    ("Norwegian",    "no", "+47",  "0150",  ["Oslo", "Bergen", "Trondheim", "Stavanger"],
     ["Karl Johans gate", "Aker Brygge", "Storgata", "Bogstadveien"]),
    ("Danish",       "dk", "+45",  "1000",  ["Copenhagen", "Aarhus", "Odense", "Aalborg"],
     ["Strøget", "Nørrebrogade", "Bredgade", "Vesterbrogade"]),
    ("Greek",        "gr", "+30",  "10431", ["Athens", "Thessaloniki", "Patras", "Heraklion"],
     ["Ermou Street", "Syntagma Sq.", "Tsimiski", "Stadiou Street"]),
    ("Serbian",      "rs", "+381", "11000", ["Belgrade", "Novi Sad", "Niš", "Subotica"],
     ["Knez Mihailova", "Terazije", "Bulevar Oslobođenja", "Vojvođanska"]),
    ("Austrian",     "at", "+43",  "1010",  ["Vienna", "Graz", "Linz", "Salzburg"],
     ["Kärntner Straße", "Mariahilfer Str.", "Graben", "Ringstraße"]),
    ("Swiss",        "ch", "+41",  "8001",  ["Zurich", "Geneva", "Basel", "Bern"],
     ["Bahnhofstrasse", "Rue du Rhône", "Freie Strasse", "Marktgasse"]),

    # ── LATAM ───────────────────────────────────────────────────────────────
    ("Brazilian",    "br", "+55",  "01310", ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador"],
     ["Avenida Paulista", "Rua Oscar Freire", "Av. Atlântica", "Rua das Flores"]),
    ("Argentine",    "ar", "+54",  "C1000", ["Buenos Aires", "Córdoba", "Rosario", "Mendoza"],
     ["Av. Corrientes", "Florida", "Callao", "Santa Fe"]),
    ("Mexican",      "mx", "+52",  "06600", ["Mexico City", "Guadalajara", "Monterrey", "Puebla"],
     ["Paseo de la Reforma", "Insurgentes", "Madero", "Juárez"]),
    ("Colombian",    "co", "+57",  "110111",["Bogotá", "Medellín", "Cali", "Barranquilla"],
     ["Calle 72", "Carrera 7", "El Poblado", "Zona Rosa"]),
    ("Chilean",      "cl", "+56",  "8320000",["Santiago", "Valparaíso", "Concepción", "La Serena"],
     ["Av. Providencia", "Paseo Ahumada", "Alameda", "Av. Italia"]),
    ("Uruguayan",    "uy", "+598", "11000", ["Montevideo", "Salto", "Paysandú", "Las Piedras"],
     ["18 de Julio", "Andes", "Colonia", "Sarandí"]),
    ("Peruvian",     "pe", "+51",  "15001", ["Lima", "Arequipa", "Cusco", "Trujillo"],
     ["Jirón de la Unión", "Av. Larco", "Av. Javier Prado", "Benavides"]),
    ("Venezuelan",   "ve", "+58",  "1010",  ["Caracas", "Maracaibo", "Valencia", "Barquisimeto"],
     ["Av. Libertador", "Sabana Grande", "Francisco de Miranda", "Las Mercedes"]),
    ("Ecuadorian",   "ec", "+593", "170136",["Quito", "Guayaquil", "Cuenca", "Ambato"],
     ["Av. Amazonas", "González Suárez", "Calle Larga", "10 de Agosto"]),
    ("Bolivian",     "bo", "+591", "0000",  ["La Paz", "Santa Cruz", "Cochabamba", "Oruro"],
     ["El Prado", "Camacho", "Av. Arce", "Murillo"]),
    ("Paraguayan",   "py", "+595", "1701",  ["Asunción", "Ciudad del Este", "San Lorenzo", "Luque"],
     ["Palma", "Chile", "Mariscal López", "Independencia Nacional"]),
    ("Costa Rican",  "cr", "+506", "10101", ["San José", "Cartago", "Heredia", "Alajuela"],
     ["Av. Central", "Calle 5", "Paseo Colón", "Av. Segunda"]),

    # ── North America ────────────────────────────────────────────────────────
    ("American",     "us", "+1",   "10001", ["New York", "Los Angeles", "Chicago", "Houston", "Miami"],
     ["Broadway", "Fifth Avenue", "Sunset Blvd", "Michigan Ave", "Brickell"]),
    ("Canadian",     "ca", "+1",   "M5V",   ["Toronto", "Vancouver", "Montreal", "Calgary"],
     ["King Street W", "Granville St", "Sainte-Catherine", "17th Ave SW"]),

    # ── Africa ──────────────────────────────────────────────────────────────
    ("Nigerian",     "ng", "+234", "101001",["Lagos", "Abuja", "Kano", "Port Harcourt"],
     ["Victoria Island", "Adeola Odeku", "Wuse II", "GRA Phase 2"]),
    ("Ghanaian",     "gh", "+233", "GA-001",["Accra", "Kumasi", "Tamale", "Cape Coast"],
     ["Oxford Street", "Liberation Road", "Ashanti Road", "Castle Road"]),
    ("Senegalese",   "sn", "+221", "12500", ["Dakar", "Thiès", "Ziguinchor", "Saint-Louis"],
     ["Avenue Bourguiba", "Rue Blanchot", "Corniche Ouest", "Rue Félix Faure"]),
    ("Cameroonian",  "cm", "+237", "237",   ["Yaoundé", "Douala", "Bamenda", "Bafoussam"],
     ["Boulevard du 20 Mai", "Rue de Nachtigal", "Akwa", "Biyem-Assi"]),
    ("Moroccan",     "ma", "+212", "20000", ["Casablanca", "Rabat", "Marrakech", "Fez"],
     ["Boulevard Mohammed V", "Avenue des FAR", "Rue de la Liberté", "Derb Chtouka"]),
    ("Egyptian",     "eg", "+20",  "11511", ["Cairo", "Alexandria", "Giza", "Luxor"],
     ["Corniche El Nil", "Tahrir Square", "El Hegaz", "Road 9"]),
    ("South African","za", "+27",  "2000",  ["Johannesburg", "Cape Town", "Durban", "Pretoria"],
     ["Sandton Drive", "Long Street", "Florida Road", "Church Street"]),
    ("Kenyan",       "ke", "+254", "00100", ["Nairobi", "Mombasa", "Kisumu", "Nakuru"],
     ["Kenyatta Avenue", "Uhuru Highway", "Moi Avenue", "Nyerere Road"]),
    ("Tunisian",     "tn", "+216", "1002",  ["Tunis", "Sfax", "Sousse", "Monastir"],
     ["Avenue Habib Bourguiba", "Rue de la Kasbah", "Av. de la Liberté", "Av. Tahar Sfar"]),
    ("Ivorian",      "ci", "+225", "01",    ["Abidjan", "Bouaké", "Daloa", "Yamoussoukro"],
     ["Boulevard Latrille", "Rue du Commerce", "Avenue Chardy", "Boulevard de Marseille"]),
    ("Algerian",     "dz", "+213", "16000", ["Algiers", "Oran", "Constantine", "Annaba"],
     ["Rue Didouche Mourad", "Boulevard Zighout Youcef", "Rue Larbi Ben M'hidi", "Avenue Soummam"]),

    # ── Asia / Pacific ───────────────────────────────────────────────────────
    ("Japanese",     "jp", "+81",  "100-0001",["Tokyo", "Osaka", "Kyoto", "Fukuoka"],
     ["Omotesando", "Shinjuku", "Dotonbori", "Nishiki Market"]),
    ("South Korean", "kr", "+82",  "03154", ["Seoul", "Busan", "Incheon", "Daegu"],
     ["Gangnam-daero", "Myeongdong", "Haeundae", "Seomyeon"]),
    ("Chinese",      "cn", "+86",  "100000",["Beijing", "Shanghai", "Guangzhou", "Shenzhen"],
     ["Wangfujing", "The Bund", "Beijing Lu", "Huaqiangbei"]),
    ("Indonesian",   "id", "+62",  "10110", ["Jakarta", "Surabaya", "Bandung", "Medan"],
     ["Jl. Sudirman", "Jl. Thamrin", "Jl. Diponegoro", "Jl. Gatot Subroto"]),
    ("Vietnamese",   "vn", "+84",  "100000",["Hanoi", "Ho Chi Minh City", "Da Nang", "Hue"],
     ["Hoàn Kiếm", "Đồng Khởi", "Bạch Đằng", "Lê Lợi"]),
    ("Australian",   "au", "+61",  "2000",  ["Sydney", "Melbourne", "Brisbane", "Perth"],
     ["George Street", "Collins Street", "Queen Street", "Hay Street"]),
    ("Indian",       "in", "+91",  "110001",["Mumbai", "Delhi", "Bangalore", "Chennai"],
     ["Marine Drive", "Connaught Place", "MG Road", "Anna Salai"]),
    ("Saudi Arabian","sa", "+966", "11564", ["Riyadh", "Jeddah", "Mecca", "Medina"],
     ["King Fahd Road", "Prince Mohammed bin Abdulaziz", "Corniche Road", "Olaya Street"]),
    ("Emirati",      "ae", "+971", "00000", ["Dubai", "Abu Dhabi", "Sharjah", "Ajman"],
     ["Sheikh Zayed Road", "Al Wasl Road", "Airport Road", "Hamdan Street"]),
    ("Turkish",      "tr", "+90",  "34000", ["Istanbul", "Ankara", "Izmir", "Bursa"],
     ["İstiklal Caddesi", "Bağdat Caddesi", "Kızılay", "Alsancak"]),
]

# ---------------------------------------------------------------------------
# Name pools per nationality (male, female, last names)
# ---------------------------------------------------------------------------
NAMES: Dict[str, Tuple[List[str], List[str], List[str]]] = {
    "German":       (["Felix","Leon","Lukas","Moritz","Finn","Jonas","Paul","Max","Erik","Tobias"],
                     ["Lena","Emma","Laura","Anna","Sophie","Mia","Clara","Lea","Nora","Jana"],
                     ["Müller","Schmidt","Schneider","Fischer","Weber","Meyer","Wagner","Becker","Hoffmann","Schulz"]),
    "French":       (["Lucas","Hugo","Théo","Nathan","Maxime","Tom","Antoine","Paul","Louis","Romain"],
                     ["Emma","Léa","Chloé","Manon","Camille","Lucie","Inès","Julie","Marie","Anaïs"],
                     ["Martin","Bernard","Dubois","Thomas","Robert","Petit","Richard","Leroy","Simon","Laurent"]),
    "Spanish":      (["Alejandro","David","Pablo","Carlos","Miguel","Javier","Álvaro","Sergio","Adrián","Iván"],
                     ["Lucía","María","Paula","Laura","Sofía","Ana","Carmen","Isabel","Elena","Andrea"],
                     ["García","Martínez","López","Sánchez","González","Pérez","Fernández","Rodríguez","Álvarez","Torres"]),
    "Italian":      (["Francesco","Alessandro","Lorenzo","Matteo","Davide","Luca","Marco","Giovanni","Andrea","Riccardo"],
                     ["Sofia","Giulia","Aurora","Alice","Giorgia","Emma","Martina","Sara","Chiara","Valentina"],
                     ["Rossi","Ferrari","Esposito","Bianchi","Romano","Colombo","Ricci","Marino","Greco","Bruno"]),
    "Dutch":        (["Daan","Lars","Tim","Sven","Bas","Tom","Rik","Joep","Bram","Koen"],
                     ["Emma","Julia","Lotte","Fleur","Nora","Amber","Iris","Roos","Anne","Isa"],
                     ["de Jong","Jansen","de Vries","van den Berg","Bakker","Visser","Smit","Meijer","de Boer","Müller"]),
    "Portuguese":   (["João","Pedro","Miguel","Diogo","Tiago","André","Rui","Ricardo","Filipe","Bruno"],
                     ["Ana","Inês","Sofia","Beatriz","Mariana","Catarina","Rita","Patrícia","Joana","Marta"],
                     ["Silva","Santos","Ferreira","Pereira","Oliveira","Costa","Rodrigues","Martins","Jesus","Sousa"]),
    "Belgian":      (["Thomas","Luca","Maxime","Noah","Lucas","Mathis","Arthur","Hugo","Louis","Nathan"],
                     ["Emma","Nora","Lena","Elise","Julie","Laura","Marie","Sofie","Hanne","Ines"],
                     ["Janssen","Peeters","Maes","Jacobs","Willems","Claes","Goossens","Hermans","Leclercq","Lambert"]),
    "Polish":       (["Marek","Piotr","Tomasz","Jan","Michał","Krzysztof","Andrzej","Adam","Łukasz","Jakub"],
                     ["Anna","Maria","Katarzyna","Małgorzata","Agnieszka","Barbara","Ewa","Joanna","Aleksandra","Natalia"],
                     ["Nowak","Kowalski","Wiśniewski","Wójcik","Kowalczyk","Kamiński","Lewandowski","Zieliński","Szymański","Woźniak"]),
    "Czech":        (["Jakub","Tomáš","Jan","Martin","Petr","Lukáš","Ondřej","Michal","David","Jiří"],
                     ["Tereza","Anna","Lucie","Petra","Markéta","Jana","Eva","Veronika","Kateřina","Lenka"],
                     ["Novák","Svoboda","Novotný","Dvořák","Černý","Procházka","Kučera","Veselý","Horák","Němec"]),
    "Hungarian":    (["Péter","Gábor","Zoltán","Ádám","Bence","Dávid","Tamás","László","Norbert","Balázs"],
                     ["Anna","Réka","Eszter","Katalin","Zsófia","Nóra","Borbála","Viktória","Petra","Orsolya"],
                     ["Nagy","Kovács","Tóth","Szabó","Horváth","Varga","Kiss","Molnár","Németh","Farkas"]),
    "Romanian":     (["Alexandru","Andrei","Mihai","Cristian","Bogdan","Ionuț","Sebastian","Florin","Radu","Gabriel"],
                     ["Maria","Ana","Elena","Ioana","Andreea","Cristina","Raluca","Mihaela","Diana","Roxana"],
                     ["Popescu","Ionescu","Popa","Gheorghe","Constantin","Stoica","Marin","Dumitru","Stan","Barbu"]),
    "Croatian":     (["Ivan","Marko","Tomislav","Josip","Ante","Luka","Stjepan","Mateo","Nikola","Filip"],
                     ["Ana","Ivana","Maja","Petra","Nina","Lucija","Marija","Katarina","Iva","Tea"],
                     ["Horvat","Kovačević","Babić","Marković","Jurić","Tomić","Novak","Knežević","Petrović","Blažević"]),
    "Swedish":      (["Erik","Johan","Lars","Magnus","Björn","Anders","Sven","Karl","Nils","Olof"],
                     ["Anna","Maria","Emma","Sara","Karin","Maja","Lena","Elin","Lisa","Frida"],
                     ["Johansson","Andersson","Karlsson","Nilsson","Eriksson","Larsson","Olsson","Persson","Svensson","Gustafsson"]),
    "Norwegian":    (["Lars","Erik","Ole","Anders","Per","Tor","Hans","Knut","Arne","Bjørn"],
                     ["Anne","Kari","Ingrid","Astrid","Mari","Hilde","Silje","Kristin","Nina","Tone"],
                     ["Hansen","Johansen","Olsen","Larsen","Andersen","Pedersen","Nilsen","Kristiansen","Jensen","Karlsen"]),
    "Danish":       (["Lars","Mads","Mikkel","Anders","Jonas","Kasper","Christian","Thomas","Daniel","Rasmus"],
                     ["Emma","Sofie","Anna","Laura","Ida","Sara","Camilla","Maja","Julie","Maria"],
                     ["Jensen","Nielsen","Hansen","Pedersen","Andersen","Christensen","Larsen","Sørensen","Rasmussen","Jørgensen"]),
    "Greek":        (["Dimitris","Nikos","Yiannis","Kostas","Giorgos","Alexandros","Panagiotis","Stelios","Christos","Vasilis"],
                     ["Maria","Elena","Katerina","Anna","Sofia","Eleni","Dimitra","Vasiliki","Ioanna","Christina"],
                     ["Papadopoulos","Papadimitriou","Oikonomou","Georgiou","Papadakis","Christodoulou","Alexiou","Petrou","Nikolaou","Antoniou"]),
    "Serbian":      (["Aleksandar","Nikola","Marko","Stefan","Miloš","Filip","Vladimir","Dragan","Bojan","Nemanja"],
                     ["Ana","Milica","Jovana","Marija","Tamara","Maja","Jelena","Nina","Katarina","Dragana"],
                     ["Jovanović","Petrović","Nikolić","Marković","Đorđević","Stojanović","Ilić","Stanković","Popović","Mihajlović"]),
    "Austrian":     (["Thomas","Stefan","Michael","David","Lukas","Florian","Andreas","Markus","Dominik","Simon"],
                     ["Laura","Anna","Lisa","Katharina","Sarah","Julia","Viktoria","Sandra","Bianca","Eva"],
                     ["Gruber","Huber","Bauer","Wagner","Müller","Pichler","Steiner","Moser","Mayer","Hofer"]),
    "Swiss":        (["Simon","Michael","Daniel","Lukas","David","Thomas","Fabian","Raphael","Julian","Patrick"],
                     ["Laura","Anna","Lena","Julia","Klara","Nicole","Sandra","Monika","Tanja","Andrea"],
                     ["Müller","Meier","Schmid","Keller","Weber","Huber","Meyer","Schneider","Fischer","Widmer"]),

    "Brazilian":    (["Lucas","Gabriel","Rafael","Gustavo","Felipe","Vinicius","Matheus","Thiago","Bruno","Eduardo"],
                     ["Julia","Ana","Beatriz","Camila","Mariana","Fernanda","Amanda","Larissa","Natalia","Gabriela"],
                     ["Silva","Santos","Oliveira","Souza","Lima","Pereira","Costa","Carvalho","Almeida","Rodrigues"]),
    "Argentine":    (["Matías","Nicolás","Ezequiel","Facundo","Agustín","Santiago","Tomás","Franco","Ignacio","Federico"],
                     ["Valentina","Florencia","Camila","Luciana","Natalia","Soledad","Vanesa","Paola","Carolina","Romina"],
                     ["González","Rodríguez","Gómez","García","López","Fernández","Sánchez","Romero","Díaz","Álvarez"]),
    "Mexican":      (["José","Juan","Carlos","Miguel","Luis","Jorge","Roberto","Alejandro","Francisco","Manuel"],
                     ["María","Ana","Rosa","Guadalupe","Patricia","Claudia","Leticia","Verónica","Adriana","Susana"],
                     ["Hernández","García","Martínez","López","González","Pérez","Rodríguez","Sánchez","Ramírez","Torres"]),
    "Colombian":    (["Andrés","Carlos","Juan","Daniel","Sebastián","Ricardo","Diego","Camilo","Alejandro","Felipe"],
                     ["Valentina","Laura","Sara","Daniela","Natalia","Paula","María","Carolina","Diana","Alejandra"],
                     ["Rodríguez","García","Martínez","Hernández","López","González","Torres","Gómez","Sánchez","Díaz"]),
    "Chilean":      (["Sebastián","Felipe","Ignacio","Rodrigo","Diego","Pablo","Camilo","Cristóbal","Matías","Gabriel"],
                     ["Valentina","Constanza","Fernanda","Javiera","Camila","Daniela","Isidora","Trinidad","Antonia","Catalina"],
                     ["González","Muñoz","Rojas","Díaz","Pérez","Soto","Contreras","Silva","Martínez","Sepúlveda"]),
    "Uruguayan":    (["Santiago","Ignacio","Nicolás","Matías","Martín","Federico","Rodrigo","Gonzalo","Pablo","Agustín"],
                     ["Valentina","Camila","Sofía","Lucía","Florencia","Ana","Martina","Natalia","Carolina","Paula"],
                     ["González","Rodríguez","García","Fernández","Martínez","Pérez","Álvarez","Sánchez","Díaz","Giménez"]),
    "Peruvian":     (["Carlos","José","Luis","Jorge","Manuel","Alberto","Ricardo","Antonio","Fernando","Eduardo"],
                     ["María","Ana","Rosa","Carmen","Paola","Diana","Valeria","Claudia","Patricia","Giovanna"],
                     ["García","Quispe","López","Mamani","Huanca","Flores","Vargas","Gutiérrez","Ramos","Chávez"]),
    "Venezuelan":   (["Carlos","José","Luis","Rafael","Jesús","Miguel","Roberto","Héctor","Antonio","Andrés"],
                     ["María","Ana","Carmen","Rosa","Valentina","Adriana","Paola","Mariela","Yolanda","Bárbara"],
                     ["González","Rodríguez","García","López","Hernández","Pérez","Díaz","Ramírez","Flores","Torres"]),
    "Ecuadorian":   (["Carlos","Juan","Luis","Jorge","Marco","Daniel","Santiago","Andrés","Sebastián","Pablo"],
                     ["María","Ana","Rosa","Verónica","Fernanda","Gabriela","Paola","Diana","Cecilia","Elena"],
                     ["García","González","Rodríguez","Morales","Herrera","Vásquez","Jiménez","Torres","Castillo","Ramírez"]),
    "Bolivian":     (["Juan","Carlos","Luis","José","Mario","Roberto","Pablo","Ricardo","Antonio","Fernando"],
                     ["María","Ana","Rosa","Carmen","Paola","Gabriela","Sandra","Lucia","Adriana","Natalia"],
                     ["Mamani","Quispe","Condori","Huanca","Choque","Flores","Apaza","Calle","Vargas","Lima"]),
    "Paraguayan":   (["Carlos","José","Juan","Luis","Pedro","Ricardo","Fernando","Diego","Alejandro","Marcos"],
                     ["María","Ana","Carmen","Rosa","Paola","Valentina","Natalia","Sandra","Verónica","Claudia"],
                     ["González","Rodríguez","García","Martínez","Pérez","López","Romero","Sánchez","Díaz","Flores"]),
    "Costa Rican":  (["Andrés","Carlos","Diego","Luis","Marco","José","Rodrigo","Pablo","Sebastián","Daniel"],
                     ["María","Ana","Laura","Fernanda","Valeria","Natalia","Paola","Diana","Camila","Sofía"],
                     ["González","Rodríguez","Hernández","García","Mora","Vargas","Jiménez","Solano","Brenes","Murillo"]),

    "American":     (["James","John","Robert","Michael","William","David","Richard","Joseph","Thomas","Charles"],
                     ["Mary","Patricia","Linda","Barbara","Elizabeth","Jennifer","Maria","Susan","Margaret","Dorothy"],
                     ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Wilson","Taylor"]),
    "Canadian":     (["Liam","Noah","Ethan","Oliver","Lucas","Mason","Logan","Ryan","Jacob","Justin"],
                     ["Emma","Olivia","Sophia","Ava","Isabella","Mia","Charlotte","Amelia","Chloe","Grace"],
                     ["Smith","Brown","Tremblay","Martin","Roy","Wilson","MacDonald","Johnson","Thompson","Taylor"]),

    "Nigerian":     (["Emeka","Chidi","Tunde","Segun","Femi","Kola","Bayo","Uche","Dele","Ayo"],
                     ["Ngozi","Chioma","Adaeze","Amaka","Blessing","Chinwe","Ifunanya","Nneka","Obiageli","Adanna"],
                     ["Okafor","Adeyemi","Obi","Eze","Chukwu","Adesanya","Nwosu","Ibrahim","Babatunde","Okonkwo"]),
    "Ghanaian":     (["Kwame","Kofi","Yaw","Kweku","Fiifi","Nana","Abena","Kwabena","Adjoa","Ama"],
                     ["Akosua","Abena","Adwoa","Ama","Akua","Afua","Efua","Esi","Mabel","Gifty"],
                     ["Asante","Mensah","Owusu","Darko","Boateng","Acheampong","Amoah","Frimpong","Adjei","Osei"]),
    "Senegalese":   (["Abdou","Mamadou","Ibrahima","Cheikh","Ousmane","Moussa","Babacar","Demba","Saliou","Modou"],
                     ["Fatou","Aminata","Mariama","Aissatou","Ndèye","Coumba","Kadiatou","Fatoumata","Rokhaya","Yacine"],
                     ["Diallo","Ndiaye","Mbaye","Sy","Diop","Sow","Fall","Sarr","Gueye","Cissé"]),
    "Cameroonian":  (["Eric","Patrick","Samuel","Martin","Emmanuel","Joseph","Victor","Christian","Jean","Didier"],
                     ["Marie","Cécile","Hortense","Sandrine","Christelle","Pauline","Nathalie","Laure","Grace","Solange"],
                     ["Nguema","Mvondo","Tchinda","Foka","Mbarga","Njoya","Abanda","Elong","Ndzie","Biya"]),
    "Moroccan":     (["Mohamed","Ahmed","Youssef","Omar","Hassan","Hamid","Rachid","Karim","Nabil","Soufiane"],
                     ["Fatima","Khadija","Zineb","Samira","Laila","Hanane","Nadia","Sara","Houda","Sanae"],
                     ["Benali","El Amrani","Berrada","Tazi","Benslimane","Alaoui","Idrissi","Benkirane","Ennaji","Chraibi"]),
    "Egyptian":     (["Mohamed","Ahmed","Ali","Omar","Hassan","Ibrahim","Mahmoud","Karim","Tarek","Amr"],
                     ["Fatima","Nour","Sara","Dina","Rania","Heba","Mona","Aya","Mariam","Salma"],
                     ["Hassan","Ali","Mohamed","Ibrahim","Ahmed","Mahmoud","Sayed","Mostafa","Abd El-Rahman","Khalil"]),
    "South African":(["Thabo","Sipho","Bongani","Nkosinathi","Siyanda","Lethiwe","Lungelo","Sandile","Mthokozisi","Sibonelo"],
                     ["Nomvula","Zanele","Thandi","Nompumelelo","Lungile","Nokuthula","Sithembile","Bongiwe","Lindiwe","Nosipho"],
                     ["Nkosi","Dlamini","Mkhize","Ntuli","Shabalala","Vilakazi","Zulu","Ndlovu","Cele","Buthelezi"]),
    "Kenyan":       (["John","David","James","Michael","Peter","Joseph","Samuel","Daniel","Paul","George"],
                     ["Mary","Grace","Faith","Ann","Joyce","Caroline","Nancy","Lucy","Susan","Esther"],
                     ["Kamau","Otieno","Mwangi","Njoroge","Odhiambo","Waweru","Kimani","Kariuki","Gitonga","Muthoni"]),
    "Tunisian":     (["Mohamed","Ahmed","Ali","Omar","Sami","Walid","Tarek","Rami","Chokri","Youssef"],
                     ["Fatima","Nour","Sara","Mariam","Ines","Olfa","Rania","Hanen","Asma","Rim"],
                     ["Ben Ali","Trabelsi","Gharbi","Sfar","Jebali","Salah","Hamdi","Souissi","Lahmar","Karray"]),
    "Ivorian":      (["Kofi","Koffi","Adou","Yao","Kouame","Konan","N'Goran","Serge","Didier","Franck"],
                     ["Marie","Adou","Aya","Adjoua","Akissi","Bintou","Mariam","Estelle","Florence","Sandrine"],
                     ["Kouassi","Diallo","Koné","Bamba","Touré","Coulibaly","Traoré","Konaté","Ouattara","Dembélé"]),
    "Algerian":     (["Mohamed","Ahmed","Karim","Yacine","Rachid","Sofiane","Riyad","Sami","Bilal","Zine"],
                     ["Fatima","Amina","Sara","Nour","Dalila","Yasmine","Lamia","Souhila","Karima","Lynda"],
                     ["Boudiaf","Mekhloufi","Ziani","Ghilas","Bougherra","Feghouli","Brahimi","Taider","Mahrez","Bennacer"]),

    "Japanese":     (["Haruto","Sota","Yuto","Hayato","Ryusei","Sho","Kaito","Daiki","Kento","Ren"],
                     ["Yui","Aoi","Hina","Rin","Moe","Saki","Riko","Yuna","Nana","Haruka"],
                     ["Sato","Suzuki","Tanaka","Watanabe","Ito","Yamamoto","Nakamura","Kobayashi","Kato","Yoshida"]),
    "South Korean": (["Jimin","Taehyung","Jungkook","Sehun","Kai","Baekhyun","Chanyeol","Suho","Hyun","Joon"],
                     ["Yuna","Somi","Chaeyoung","Nayeon","Jisoo","Jennie","Rosé","Lisa","Seulgi","Irene"],
                     ["Kim","Lee","Park","Choi","Jeong","Han","Im","Oh","Seo","Yoon"]),
    "Chinese":      (["Wei","Hao","Yang","Lei","Tao","Chen","Fang","Jie","Xin","Kai"],
                     ["Xin","Ying","Fang","Li","Jing","Na","Hong","Yan","Mei","Qing"],
                     ["Wang","Li","Zhang","Liu","Chen","Yang","Huang","Zhao","Wu","Zhou"]),
    "Indonesian":   (["Budi","Andi","Rizky","Fajar","Dian","Reza","Hendra","Wahyu","Agus","Bayu"],
                     ["Sari","Dewi","Indah","Ratna","Yeni","Wulan","Putri","Ani","Nia","Dini"],
                     ["Santoso","Suharto","Wibowo","Kusuma","Prasetyo","Nugroho","Purnomo","Setiawan","Hartono","Wahyudi"]),
    "Vietnamese":   (["Minh","Hùng","Nam","Tuấn","Đức","Hải","Long","Quang","Dũng","Bình"],
                     ["Lan","Hoa","Thu","Linh","Mai","Thảo","Phương","Hương","Ngọc","Ánh"],
                     ["Nguyễn","Trần","Lê","Phạm","Huỳnh","Phan","Vũ","Đặng","Bùi","Đỗ"]),
    "Australian":   (["Jack","Oliver","William","Noah","Thomas","James","Henry","Liam","Ethan","Lucas"],
                     ["Charlotte","Olivia","Amelia","Ava","Mia","Isla","Grace","Lily","Chloe","Sophie"],
                     ["Smith","Jones","Williams","Brown","Wilson","Taylor","Johnson","White","Martin","Anderson"]),
    "Indian":       (["Rahul","Arjun","Vikram","Rohit","Amit","Sanjay","Arun","Suresh","Raj","Pradeep"],
                     ["Priya","Anjali","Neha","Divya","Pooja","Sneha","Kavya","Ananya","Riya","Meera"],
                     ["Sharma","Singh","Patel","Kumar","Gupta","Verma","Joshi","Rao","Nair","Reddy"]),
    "Saudi Arabian":(["Mohammed","Abdullah","Abdulrahman","Faisal","Sultan","Fahad","Khalid","Saad","Bandar","Turki"],
                     ["Sara","Nora","Layan","Reem","Ghada","Maha","Hessa","Dalal","Taghreed","Rasha"],
                     ["Al-Ghamdi","Al-Zahrani","Al-Qahtani","Al-Shehri","Al-Otaibi","Al-Harbi","Al-Dossari","Al-Asmari","Al-Mutairi","Al-Malki"]),
    "Emirati":      (["Mohammed","Ahmed","Khalid","Sultan","Saeed","Omar","Hamdan","Mansoor","Rashed","Mubarak"],
                     ["Fatima","Mariam","Sara","Hessa","Noura","Aisha","Latifa","Maitha","Shamsa","Moza"],
                     ["Al-Mansoori","Al-Mazrouei","Al-Shamsi","Al-Maktoum","Al-Nahyan","Al-Suwaidi","Al-Ketbi","Al-Kaabi","Al-Rashidi","Al-Blooshi"]),
    "Turkish":      (["Emre","Mert","Can","Arda","Burak","Kerem","Berkay","Kaan","Mehmet","Ali"],
                     ["Elif","Zeynep","Selin","Ayşe","Fatma","Esra","Melis","Deniz","Büşra","Ceren"],
                     ["Yılmaz","Kaya","Demir","Şahin","Çelik","Yıldız","Yıldırım","Özdemir","Arslan","Doğan"]),
}

# ---------------------------------------------------------------------------
# Distribution: how many players per country  (sums to 1024)
# ---------------------------------------------------------------------------
DISTRIBUTION = {
    # EU ~300
    "German": 18, "French": 18, "Spanish": 18, "Italian": 18, "Dutch": 16,
    "Portuguese": 16, "Belgian": 14, "Polish": 18, "Czech": 14, "Hungarian": 18,
    "Romanian": 16, "Croatian": 14, "Swedish": 16, "Norwegian": 14, "Danish": 14,
    "Greek": 16, "Serbian": 14, "Austrian": 14, "Swiss": 14,
    # LATAM ~200
    "Brazilian": 24, "Argentine": 20, "Mexican": 24, "Colombian": 18, "Chilean": 16,
    "Uruguayan": 14, "Peruvian": 14, "Venezuelan": 14, "Ecuadorian": 14, "Bolivian": 12,
    "Paraguayan": 12, "Costa Rican": 12,
    # NA ~102
    "American": 62, "Canadian": 44,
    # Africa ~204
    "Nigerian": 22, "Ghanaian": 18, "Senegalese": 16, "Cameroonian": 16, "Moroccan": 20,
    "Egyptian": 20, "South African": 20, "Kenyan": 18, "Tunisian": 16, "Ivorian": 16, "Algerian": 18,
    # Asia/Pacific ~224
    "Japanese": 24, "South Korean": 24, "Chinese": 24, "Indonesian": 22, "Vietnamese": 22,
    "Australian": 22, "Indian": 24, "Saudi Arabian": 20, "Emirati": 18, "Turkish": 24,
}

assert sum(DISTRIBUTION.values()) == 1024, f"Sum is {sum(DISTRIBUTION.values())}, expected 1024"

POSITIONS = ["goalkeeper", "defender", "midfielder", "forward"]
GENDERS = ["Male", "Female"]

# Country lookup: nationality -> country entry
COUNTRY_LOOKUP = {c[0]: c for c in COUNTRIES}


def deterministic_dob(seed_int: int) -> str:
    """Generate a DOB for a player aged 17-35 (born 1991-2008), deterministic."""
    base = date(1991, 1, 1)
    offset = (seed_int * 37 + 13) % (365 * 17)  # spread over 17 years
    d = base + timedelta(days=offset)
    return d.strftime("%Y-%m-%d")


def slugify(name: str) -> str:
    """Convert name to lowercase ASCII-safe slug for email."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_str.lower().replace(" ", "").replace("'", "").replace("-", "")


def generate_players() -> List[dict]:
    players = []
    global_idx = 0

    for nationality, count in DISTRIBUTION.items():
        country_entry = COUNTRY_LOOKUP[nationality]
        country_name, iso2, phone_prefix, postal, cities, streets = country_entry
        males, females, last_names = NAMES[nationality]

        country_idx = 0
        for i in range(count):
            global_idx += 1
            country_idx += 1

            # Deterministic seeding (no random — fully reproducible)
            gender = GENDERS[i % 2]
            first_names_pool = males if gender == "Male" else females
            fn_pick = first_names_pool[i % len(first_names_pool)]
            ln_pick = last_names[i % len(last_names)]
            city = cities[i % len(cities)]
            street = streets[i % len(streets)]
            position = POSITIONS[i % 4]

            fn_slug = slugify(fn_pick)
            ln_slug = slugify(ln_pick)

            email = f"{fn_slug}.{ln_slug}.{iso2}{country_idx:03d}@lfa-seed.hu"
            # Make phone unique: prefix + 6-digit index
            phone_digits = f"{global_idx:06d}"
            phone = f"{phone_prefix}{phone_digits}"

            dob = deterministic_dob(global_idx)

            # Credit balance: deterministic 300-800 range
            credit_balance = 300 + (global_idx * 7 % 501)

            player = {
                "email": email,
                "password": "LfaScale2026!",
                "role": "STUDENT",
                "name": f"{fn_pick} {ln_pick}",
                "first_name": fn_pick,
                "last_name": ln_pick,
                "date_of_birth": dob,
                "phone": phone,
                "nationality": nationality,
                "gender": gender,
                "position": position,
                "specialization": "LFA_FOOTBALL_PLAYER",
                "onboarding_completed": True,
                "payment_verified": True,
                "credit_balance": credit_balance,
                "address": {
                    "street": f"{street} {(i % 99) + 1}.",
                    "city": city,
                    "postal_code": postal,
                    "country": country_name,
                },
                "licenses": [
                    {
                        "specialization_type": "LFA_FOOTBALL_PLAYER",
                        "current_level": 1,
                        "is_active": True,
                    }
                ],
            }
            players.append(player)

    return players


def verify_uniqueness(players: List[dict]) -> None:
    emails = [p["email"] for p in players]
    assert len(emails) == len(set(emails)), (
        f"Duplicate emails found! {len(emails) - len(set(emails))} duplicates"
    )
    print(f"  ✓ All {len(emails)} emails are unique")


def generate_api_format(players: List[dict]) -> dict:
    """Also generate the API-compatible format (batch-create-players)."""
    return {
        "players": [
            {
                "email": p["email"],
                "password": p["password"],
                "name": p["name"],
                "date_of_birth": p["date_of_birth"],
            }
            for p in players
        ],
        "specialization": "LFA_FOOTBALL_PLAYER",
        "skip_existing": True,
    }


def main():
    project_root = Path(__file__).parent.parent
    fixtures_dir = project_root / "tests" / "playwright" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  GENERATING 1024 GLOBAL PLAYER SEED")
    print("=" * 65)
    print(f"\n  Countries  : {len(DISTRIBUTION)}")
    print(f"  Total users: {sum(DISTRIBUTION.values())}")

    print("\n  Generating players...")
    players = generate_players()
    print(f"  ✓ Generated {len(players)} players")

    print("\n  Verifying uniqueness...")
    verify_uniqueness(players)

    # Distribution summary
    print("\n  Regional distribution:")
    eu = sum(v for k, v in DISTRIBUTION.items() if COUNTRY_LOOKUP[k][0] in
             ["German","French","Spanish","Italian","Dutch","Portuguese","Belgian","Polish",
              "Czech","Hungarian","Romanian","Croatian","Swedish","Norwegian","Danish",
              "Greek","Serbian","Austrian","Swiss"])
    latam = sum(v for k, v in DISTRIBUTION.items() if COUNTRY_LOOKUP[k][0] in
                ["Brazilian","Argentine","Mexican","Colombian","Chilean","Uruguayan","Peruvian",
                 "Venezuelan","Ecuadorian","Bolivian","Paraguayan","Costa Rican"])
    na = sum(v for k, v in DISTRIBUTION.items() if COUNTRY_LOOKUP[k][0] in ["American","Canadian"])
    africa = sum(v for k, v in DISTRIBUTION.items() if COUNTRY_LOOKUP[k][0] in
                 ["Nigerian","Ghanaian","Senegalese","Cameroonian","Moroccan","Egyptian",
                  "South African","Kenyan","Tunisian","Ivorian","Algerian"])
    asia = sum(v for k, v in DISTRIBUTION.items() if COUNTRY_LOOKUP[k][0] in
               ["Japanese","South Korean","Chinese","Indonesian","Vietnamese","Australian",
                "Indian","Saudi Arabian","Emirati","Turkish"])
    print(f"    EU            : {eu:4d}")
    print(f"    LATAM         : {latam:4d}")
    print(f"    North America : {na:4d}")
    print(f"    Africa        : {africa:4d}")
    print(f"    Asia/Pacific  : {asia:4d}")
    print(f"    TOTAL         : {eu+latam+na+africa+asia:4d}")

    # Write seed_from_json.py format
    seed_data = {
        "_meta": {
            "description": "1024 global production-structure players for scale validation",
            "generated_by": "scripts/generate_1024_global_seed.py",
            "import_via": "python scripts/seed_from_json.py --fixture=seed_1024_global_players",
            "api_import_via": "POST /api/v1/admin/batch-create-players (use seed_1024_global_players_api.json)",
            "countries": len(DISTRIBUTION),
            "total_users": len(players),
            "fields": ["email","password","role","name","first_name","last_name",
                       "date_of_birth","phone","nationality","gender","position",
                       "specialization","onboarding_completed","payment_verified",
                       "credit_balance","address","licenses"],
        },
        "users": players,
        "locations": [],
        "tournaments": [],
        "coupons": [],
    }

    out_path = fixtures_dir / "seed_1024_global_players.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(seed_data, f, ensure_ascii=False, indent=2)
    size_kb = out_path.stat().st_size // 1024
    print(f"\n  ✓ Written: {out_path}")
    print(f"    Size: {size_kb} KB")

    # Write API format (batch-create-players)
    api_data = generate_api_format(players)
    api_path = fixtures_dir / "seed_1024_global_players_api.json"
    with open(api_path, "w", encoding="utf-8") as f:
        json.dump(api_data, f, ensure_ascii=False, indent=2)
    api_size_kb = api_path.stat().st_size // 1024
    print(f"  ✓ Written: {api_path}")
    print(f"    Size: {api_size_kb} KB")

    print(f"\n{'='*65}")
    print(f"  IMPORT COMMANDS")
    print(f"{'='*65}")
    print(f"\n  Via seed script (full fields):")
    print(f"    DATABASE_URL=\"...\" python scripts/seed_from_json.py \\")
    print(f"      --fixture=seed_1024_global_players")
    print(f"\n  Via API (email/password/name/dob only):")
    print(f"    TOKEN=$(curl -s -X POST .../api/v1/auth/login \\")
    print(f"      -d '{{\"email\":\"admin@lfa.com\",\"password\":\"admin123\"}}' | jq -r .access_token)")
    print(f"    curl -X POST .../api/v1/admin/batch-create-players \\")
    print(f"      -H \"Authorization: Bearer $TOKEN\" \\")
    print(f"      -H \"Content-Type: application/json\" \\")
    print(f"      -d @tests/playwright/fixtures/seed_1024_global_players_api.json")
    print(f"\n{'='*65}")
    print(f"  DONE — {len(players)} players ready for import")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
