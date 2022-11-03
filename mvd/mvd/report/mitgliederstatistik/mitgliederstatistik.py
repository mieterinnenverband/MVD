# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

'''
    controll query:
    SELECT
        COUNT(`name`) AS `qty`,
        `status_c`
    FROM `tabMitgliedschaft`
    WHERE `status_c` != 'Regulär'
    AND `eintrittsdatum` IS NOT NULL
    AND `sektion_id` = 'MVAG'
    OR `austritt` IS NULL 
    OR `wegzug` IS NULL 
    OR `kuendigung` IS NULL 
    GROUP BY `status_c`
'''

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return[
        {"label": _("Mitglieder"), "fieldname": "mitglieder", "fieldtype": "Data", "width": 150},
        {"label": _("Berechnung"), "fieldname": "berechnung", "fieldtype": "Data", "width": 580},
        {"label": _("Anzahl"), "fieldname": "anzahl", "fieldtype": "Data"},
        {"label": _("Total"), "fieldname": "total", "fieldtype": "Data"}
    ]

def get_data(filters):
    data = []
    data, stand_1, neumitglieder, zuzueger = get_stand(filters, data)
    # ~ data, personen_qty = get_personen_in_db(filters, data)
    data, wegzueger_qty = get_wegzueger(filters, data)
    data, kuendigungen_qty = get_kuendigungen(filters, data)
    # ~ data, vorgem_kuendigungen_qty = get_vorgem_kuendigungen(filters, data)
    data, ausschluesse_qty = get_ausschluesse(filters, data)
    data, gestorbene_qty = get_gestorbene(filters, data)
    data = get_stand_2(filters, data, stand_1, neumitglieder, zuzueger, wegzueger_qty, kuendigungen_qty, ausschluesse_qty, gestorbene_qty)
    data = get_spaetere_eintritte(filters, data)
    data = get_vorgem_kuendigungen_2(filters, data)
    data = get_ueberschrift_1(filters, data)
    data = get_erben(filters, data)
    data = get_ohne_mitgliednummer(filters, data)
    data = get_nicht_bezahlt(filters, data)
    data = get_ueberschrift_2(filters, data)
    data = get_interessiert(filters, data)
    # ~ data = get_angemeldet(filters, data)
    return data

def get_stand(filters, data):
    '''
        neumitglieder: Alle Mitglieder mit Eintrittsdatuem zwischen from_date und to_date und keinem Zuzugsdatum
    '''
    neumitglieder = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabMitgliedschaft`
                                    WHERE `eintrittsdatum` BETWEEN '{from_date}' AND '{to_date}'
                                    AND `zuzug` IS NULL
                                    AND `sektion_id` = '{sektion_id}'""".format(from_date=filters.from_date, \
                                    to_date=filters.to_date, sektion_id=filters.sektion_id), as_dict=True)[0].qty
    
    '''
        zuzueger: Alle Mitgliedschaften mit Zuzugsdatum zwischen from_date und to_date
    '''
    zuzueger = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabMitgliedschaft`
                                WHERE `zuzug` BETWEEN '{from_date}' AND '{to_date}'
                                AND `sektion_id` = '{sektion_id}'""".format(from_date=filters.from_date, \
                                to_date=filters.to_date, sektion_id=filters.sektion_id), as_dict=True)[0].qty
    
    alle_per_from_date = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabMitgliedschaft`
                                        WHERE `sektion_id` = '{sektion_id}'
                                        AND (`eintrittsdatum` <= '{from_date}' AND `eintrittsdatum` IS NOT NULL)
                                        AND (`zuzug` <= '{from_date}' OR `zuzug` IS NULL)
                                        AND (`austritt` > '{from_date}' OR `austritt` IS NULL)
                                        AND (`kuendigung` > '{from_date}' OR `kuendigung` IS NULL)""".format(from_date=filters.from_date, \
                                        to_date=filters.to_date, sektion_id=filters.sektion_id), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'Stand',
            'berechnung': '{from_date} (Total)'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y')),
            'anzahl': '',
            'total': alle_per_from_date
        })
    data.append(
        {
            'mitglieder': 'Neumitglieder',
            'berechnung': 'Eintrittsdatum {from_date} bis {to_date}'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y'), \
            to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': neumitglieder,
            'total': ''
        })
    data.append(
        {
            'mitglieder': 'Zuzüger',
            'berechnung': 'Zuzugsdatum {from_date} bis {to_date}'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y'), \
            to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': zuzueger,
            'total': ''
        })
    data.append(
        {
            'mitglieder': 'Zwischentotal',
            'berechnung': 'Stand + Neumitglieder + Zuzüger',
            'anzahl': '',
            'total': alle_per_from_date + neumitglieder + zuzueger
        })
    return data, alle_per_from_date, neumitglieder, zuzueger

# ~ def get_personen_in_db(filters, data):
    # ~ # ---
    # ~ # Achtung: Online-Beitritte sind hier mit dabei (bei Miveba nicht)
    # ~ # ---
    # ~ alle = frappe.db.sql("""SELECT
                                    # ~ COUNT(`name`) AS `qty`
                                # ~ FROM `tabMitgliedschaft`
                                # ~ WHERE `sektion_id` = '{sektion_id}'
                                # ~ AND `status_c` NOT IN ('Inaktiv', 'Wegzug')
                                # ~ AND `eintrittsdatum` <= '{to_date}'""".format(sektion_id=filters.sektion_id, to_date=filters.to_date), as_dict=True)[0].qty
    # ~ data.append(
        # ~ {
            # ~ 'mitglieder': 'Total',
            # ~ 'berechnung': 'Personen in der Datenbank mit Eintrittsdatum <= {to_date}'.format(to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            # ~ 'anzahl': '',
            # ~ 'total': alle
        # ~ })
    # ~ return data, alle

def get_wegzueger(filters, data):
    wegzueger = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabMitgliedschaft`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `wegzug` BETWEEN '{from_date}' AND '{to_date}'""".format(sektion_id=filters.sektion_id, \
                                from_date=filters.from_date, to_date=filters.to_date), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'Wegzüge',
            'berechnung': 'Wegzugsdatum {from_date} bis {to_date}'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y'), \
            to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': wegzueger,
            'total': ''
        })
    return data, wegzueger

def get_kuendigungen(filters, data):
    kuendigungen = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabMitgliedschaft`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `kuendigung` BETWEEN '{from_date}' AND '{to_date}'
                                AND `austritt` IS NULL""".format(sektion_id=filters.sektion_id, \
                                from_date=filters.from_date, to_date=filters.to_date), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'Kündigungen',
            'berechnung': 'Kündigungen per {from_date} bis {to_date}'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y'), \
            to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': kuendigungen,
            'total': ''
        })
    return data, kuendigungen

# ~ def get_vorgem_kuendigungen(filters, data):
    # ~ kuendigungen = frappe.db.sql("""SELECT
                                    # ~ COUNT(`name`) AS `qty`
                                # ~ FROM `tabMitgliedschaft`
                                # ~ WHERE `sektion_id` = '{sektion_id}'
                                # ~ AND `kuendigung` BETWEEN '{from_date}' AND '{to_date}'
                                # ~ AND `status_c` = 'Regulär'""".format(sektion_id=filters.sektion_id, \
                                # ~ from_date=filters.from_date, to_date=filters.to_date), as_dict=True)[0].qty
    # ~ data.append(
        # ~ {
            # ~ 'mitglieder': 'vorgem. Kündigungen',
            # ~ 'berechnung': 'Kündigungsdatum {from_date} bis {to_date}'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y'), \
            # ~ to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            # ~ 'anzahl': kuendigungen,
            # ~ 'total': ''
        # ~ })
    # ~ return data, kuendigungen

def get_ausschluesse(filters, data):
    # ~ ausschluesse = frappe.db.sql("""SELECT DISTINCT
                                    # ~ COUNT(`name`) AS `qty`
                                # ~ FROM `tabStatus Change`
                                # ~ WHERE `parent` IN (
                                    # ~ SELECT
                                        # ~ `name`
                                    # ~ FROM `tabMitgliedschaft`
                                    # ~ WHERE `sektion_id` = '{sektion_id}'
                                    # ~ AND `status_c` IN ('Ausschluss', 'Inaktiv')
                                    # ~ AND `austritt` BETWEEN '{from_date}' AND '{to_date}'
                                # ~ )
                                # ~ AND `status_alt` = 'Ausschluss'
                                # ~ AND `status_neu` = 'Inaktiv'""".format(sektion_id=filters.sektion_id, \
                                # ~ from_date=filters.from_date, to_date=filters.to_date), as_dict=True)[0].qty
    
    ausschluesse = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabMitgliedschaft`
                                    WHERE `sektion_id` = '{sektion_id}'
                                    AND `austritt` BETWEEN '{from_date}' AND '{to_date}'
                                    AND `verstorben_am` IS NULL""".format(sektion_id=filters.sektion_id, \
                                from_date=filters.from_date, to_date=filters.to_date), as_dict=True)[0].qty
    
    data.append(
        {
            'mitglieder': 'Ausschlüsse',
            'berechnung': 'Ausschlussdatum {from_date} bis {to_date}'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y'), \
            to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': ausschluesse,
            'total': ''
        })
    return data, ausschluesse

def get_gestorbene(filters, data):
    # ~ gestorbene = frappe.db.sql("""SELECT DISTINCT
                                    # ~ COUNT(`name`) AS `qty`
                                # ~ FROM `tabStatus Change`
                                # ~ WHERE `parent` IN (
                                    # ~ SELECT
                                        # ~ `name`
                                    # ~ FROM `tabMitgliedschaft`
                                    # ~ WHERE `sektion_id` = '{sektion_id}'
                                    # ~ AND `status_c` IN ('Gestorben', 'Inaktiv')
                                    # ~ AND `austritt` BETWEEN '{from_date}' AND '{to_date}'
                                # ~ )
                                # ~ AND `status_alt` = 'Gestorben'
                                # ~ AND `status_neu` = 'Inaktiv'""".format(sektion_id=filters.sektion_id, \
                                # ~ from_date=filters.from_date, to_date=filters.to_date), as_dict=True)[0].qty
    
    gestorbene = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabMitgliedschaft`
                                    WHERE `sektion_id` = '{sektion_id}'
                                    AND `austritt` BETWEEN '{from_date}' AND '{to_date}'
                                    AND `verstorben_am` IS NOT NULL""".format(sektion_id=filters.sektion_id, \
                                from_date=filters.from_date, to_date=filters.to_date), as_dict=True)[0].qty
    
    data.append(
        {
            'mitglieder': 'Gestorbene',
            'berechnung': 'Todesfall/Meldung mit Mitgliedschaftsende {from_date} bis {to_date}'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y'), \
            to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': gestorbene,
            'total': ''
        })
    return data, gestorbene

def get_erben(filters, data):
    
    erben = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabMitgliedschaft`
                                    WHERE `sektion_id` = '{sektion_id}'
                                    AND `austritt` > '{to_date}'
                                    AND `verstorben_am` BETWEEN '{from_date}' AND '{to_date}""".format(sektion_id=filters.sektion_id, \
                                from_date=filters.from_date, to_date=filters.to_date), as_dict=True)[0].qty
    
    data.append(
        {
            'mitglieder': 'Erben',
            'berechnung': 'Todesfall/Meldung {from_date} bis {to_date} Mitgliedschaft weitergeführt'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y'), \
            to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': erben,
            'total': ''
        })
    return data

def get_stand_2(filters, data, stand_1, neumitglieder, zuzueger, wegzueger_qty, kuendigungen_qty, ausschluesse_qty, gestorbene_qty):
    qty = (stand_1 + neumitglieder + zuzueger) - wegzueger_qty - kuendigungen_qty - ausschluesse_qty - gestorbene_qty
    
    alle_per_to_date = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabMitgliedschaft`
                                        WHERE `sektion_id` = '{sektion_id}'
                                        `eintrittsdatum` <= '{to_date}'
                                        AND (`austritt` > '{to_date}' OR `austritt` IS NULL)
                                        AND (`kuendigung` > '{to_date}' OR `kuendigung` IS NULL)""".format(from_date=filters.from_date, \
                                        to_date=filters.to_date, sektion_id=filters.sektion_id), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'Stand Query',
            'berechnung': '{to_date} (Total aktive Mitgliedschaften ohne Wegzüge, Kündigungen, Ausschlüsse, Gestorbene)'.format(to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': '',
            'total': alle_per_to_date
        })
    
    data.append(
        {
            'mitglieder': 'Stand berechnet',
            'berechnung': '{to_date} (Total aktive Mitgliedschaften ohne Wegzüge, Kündigungen, Ausschlüsse, Gestorbene)'.format(to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': '',
            'total': qty
        })
    
    return data

def get_spaetere_eintritte(filters, data):
    spaetere_eintritte = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabMitgliedschaft`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `eintrittsdatum` > '{to_date}'
                                AND `status_c` = 'Regulär'""".format(sektion_id=filters.sektion_id, \
                                to_date=filters.to_date), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'spätere Eintritte',
            'berechnung': 'Aktive Mitgliedschaften mit Eintrittsdatum > {to_date}'.format(to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': spaetere_eintritte,
            'total': ''
        })
    return data

def get_vorgem_kuendigungen_2(filters, data):
    kuendigungen = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabMitgliedschaft`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `kuendigung` > '{to_date}'
                                AND `status_c` NOT IN ('Ausschluss', 'Gestorben', 'Wegzug')""".format(sektion_id=filters.sektion_id, \
                                to_date=filters.to_date), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'vorgem. Kündigungen',
            'berechnung': 'Kündigungsdatum > {to_date} und Status nicht Ausschluss, Gestorben oder Wegzug'.format(from_date=frappe.utils.get_datetime(filters.from_date).strftime('%d.%m.%Y'), \
            to_date=frappe.utils.get_datetime(filters.to_date).strftime('%d.%m.%Y')),
            'anzahl': kuendigungen,
            'total': ''
        })
    return data

def get_ohne_mitgliednummer(filters, data):
    ohne_mitgliednummer = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabMitgliedschaft`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `mitglied_nr` = 'MV'
                                AND `status_c` != 'Interessent*in'""".format(sektion_id=filters.sektion_id), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'ohne Mitgliednummer',
            'berechnung': 'Neumitglieder ohne Nummer',
            'anzahl': ohne_mitgliednummer,
            'total': ''
        })
    return data

def get_nicht_bezahlt(filters, data):
    year = int(frappe.utils.get_datetime(filters.to_date).strftime('%Y'))
    nicht_bezahlt = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabMitgliedschaft`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `bezahltes_mitgliedschaftsjahr` < {year}
                                AND `wegzug` IS NULL
                                AND `austritt` IS NULL
                                AND `status_c` = 'Regulär'""".format(sektion_id=filters.sektion_id, year=year), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'nicht bezahlt Mitglieder ({year})'.format(year=year),
            'berechnung': 'nicht bezahlt und weder Datum Wegzug noch Datum Austritt',
            'anzahl': nicht_bezahlt,
            'total': ''
        })
    
    nicht_bezahlt = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabMitgliedschaft`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `bezahltes_mitgliedschaftsjahr` < {year}
                                AND `wegzug` IS NULL
                                AND `austritt` IS NULL
                                AND `status_c` IN ('Anmeldung', 'Online-Anmeldung')""".format(sektion_id=filters.sektion_id, year=year), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'nicht bezahlt Anmeldung ({year})'.format(year=year),
            'berechnung': 'nicht bezahlt und weder Datum Wegzug noch Datum Austritt',
            'anzahl': nicht_bezahlt,
            'total': ''
        })
    return data

def get_interessiert(filters, data):
    interessiert = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabMitgliedschaft`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `status_c` = 'Interessent*in'""".format(sektion_id=filters.sektion_id), as_dict=True)[0].qty
    data.append(
        {
            'mitglieder': 'Interessent*innen',
            'berechnung': '',
            'anzahl': interessiert,
            'total': ''
        })
    return data

# ~ def get_angemeldet(filters, data):
    # ~ angemeldet = frappe.db.sql("""SELECT
                                    # ~ COUNT(`name`) AS `qty`
                                # ~ FROM `tabMitgliedschaft`
                                # ~ WHERE `sektion_id` = '{sektion_id}'
                                # ~ AND `status_c` IN ('Anmeldung', 'Online-Anmeldung')""".format(sektion_id=filters.sektion_id), as_dict=True)[0].qty
    # ~ data.append(
        # ~ {
            # ~ 'mitglieder': 'angemeldet',
            # ~ 'berechnung': '',
            # ~ 'anzahl': angemeldet,
            # ~ 'total': ''
        # ~ })
    # ~ return data

def get_ueberschrift_1(filters, data):
    data.append(
        {
            'mitglieder': '',
            'berechnung': 'in obiger Aufstellung bereits enthalten:',
            'anzahl': '',
            'total': ''
        })
    return data

def get_ueberschrift_2(filters, data):
    data.append(
        {
            'mitglieder': '',
            'berechnung': 'in obiger Aufstellung nicht enthalten:',
            'anzahl': '',
            'total': ''
        })
    return data
