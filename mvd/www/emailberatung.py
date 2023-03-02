from __future__ import unicode_literals
import frappe
import json
import jwt
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr, prepare_mvm_for_sp
from frappe.core.doctype.communication.email import make
from frappe.desk.form.load import get_attachments
from frappe.utils import get_url, sanitize_html
from frappe import sendmail
from mvd.mvd.service_plattform.api import send_beratung
from frappe.utils.data import get_datetime_str

no_cache = 1

def get_context(context):
    authorization_header = frappe.get_request_header("Cookie", None)
    jwt_token = None
    
    if authorization_header:
        for cookie in authorization_header.split(";"):
            if cookie.startswith(" jwt_auth="):
                jwt_token = cookie.split(" jwt_auth=")[1]
            elif cookie.startswith("jwt_auth="):
                jwt_token = cookie.split("jwt_auth=")[1]
    
    if jwt_token:
        public_key = frappe.db.get_single_value('JWT', 'public_key')
        algorythmus = frappe.db.get_single_value('JWT', 'algorythmus')
        decoded_jwt_token = jwt.decode(jwt_token, public_key, algorithms=[algorythmus])
        context.jwt_token = decoded_jwt_token
        if 'mitglied_nr' in decoded_jwt_token:
            mitglied_id = get_mitglied_id_from_nr(decoded_jwt_token["mitglied_nr"])
            if mitglied_id:
                if frappe.db.exists("Mitgliedschaft", mitglied_id):
                    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
                    context = context_erweiterung(context, mitgliedschaft)
                else:
                    # Mitglied-ID in ERPNext unbekannt
                    frappe.log_error("{0}\n\n{1}".format(str(mitglied_id), str(authorization_header)), 'E-Mail Beratung (500)')
                    raise_redirect(typ='500')
            else:
                # Mitglied-ID in ERPNext unbekannt
                frappe.log_error("{0}\n\n{1}".format(str(decoded_jwt_token["mitglied_nr"]), str(authorization_header)), 'E-Mail Beratung (500)')
                raise_redirect(typ='500')
        else:
            # ungültiger JWT Token
            frappe.log_error("{0}".format(str(authorization_header)), 'E-Mail Beratung (ungültiger JWT Token)')
            raise_redirect()
    else:
        # KEIN JWT Token
        frappe.log_error("{0}".format(str(authorization_header)), 'E-Mail Beratung (KEIN JWT Token)')
        raise_redirect()

def raise_redirect(typ=None):
    if not typ:
        frappe.local.flags.redirect_location = "/nologin"
        raise frappe.Redirect
    else:
        if typ == '500':
            frappe.local.flags.redirect_location = "/mvd-500"
            raise frappe.Redirect

def context_erweiterung(context, mitgliedschaft):
    context.mitglied_nr = mitgliedschaft.mitglied_nr
    context.mitglied_id = mitgliedschaft.name
    context.anrede = mitgliedschaft.anrede_c
    context.vorname = mitgliedschaft.vorname_1
    context.nachname = mitgliedschaft.nachname_1
    context.telefon = mitgliedschaft.tel_m_1 if mitgliedschaft.tel_m_1 else mitgliedschaft.tel_p_1 if mitgliedschaft.tel_p_1 else mitgliedschaft.tel_g_1 if mitgliedschaft.tel_g_1 else ''
    context.email = mitgliedschaft.e_mail_1 if mitgliedschaft.e_mail_1 else ''
    context.sektion = mitgliedschaft.sektion_id
    
    if mitgliedschaft.abweichende_objektadresse:
        context.strasse = mitgliedschaft.objekt_strasse
        context.nummer = mitgliedschaft.objekt_hausnummer
        context.nummer_zu = mitgliedschaft.objekt_nummer_zu
        context.plz = mitgliedschaft.objekt_plz
        context.ort = mitgliedschaft.objekt_ort
    else:
        context.strasse = mitgliedschaft.strasse
        context.nummer = mitgliedschaft.nummer
        context.nummer_zu = mitgliedschaft.nummer_zu
        context.plz = mitgliedschaft.plz
        context.ort = mitgliedschaft.ort
    
    # legacy mode check
    if frappe.db.get_value("Sektion", mitgliedschaft.sektion_id, 'legacy_mode') == '2':
        context.legacy_mode = True
    else:
        context.legacy_mode = False
    
    return context

@frappe.whitelist(allow_guest=True)
def new_beratung(**kwargs):
    args = json.loads(kwargs['kwargs'])
    frappe.log_error("{0}".format(str(args)), "Neue Beratung wird angelegt (OK)")
    if frappe.db.exists("Mitgliedschaft", args['mv_mitgliedschaft']):
        if args['telefon']:
            telefon = """<b>Telefon:</b> {0}<br>""".format(args['telefon'])
        else:
            telefon = ''
        if args['email']:
            email = """<b>E-Mail:</b> {0}<br>""".format(args['email'])
        else:
            email = ''
        if args['anderes_mietobjekt']:
            anderes_mietobjekt = """<b>Anderes Mietobjekt:</b><br>{0}<br><br>""".format(sanitize_html(args['anderes_mietobjekt']).replace("\n", "<br>"))
        else:
            anderes_mietobjekt = ''
        if args['frage']:
            frage = """<b>Frage:</b><br>{0}<br><br>""".format(sanitize_html(args['frage']).replace("\n", "<br>"))
        else:
            frage = ''
        if args['datum_mietzinsanzeige']:
            datum_mietzinsanzeige = """<b>Briefdatum der Mietzinserhöhungsanzeige:</b> {0}""".format(args['datum_mietzinsanzeige'])
        else:
            datum_mietzinsanzeige = ''
        
        notiz = """{0}{1}{2}{3}{4}""".format(telefon, email, anderes_mietobjekt, frage, datum_mietzinsanzeige)
        
        new_ber = frappe.get_doc({
            'doctype': 'Beratung',
            'status': 'Eingang',
            'mv_mitgliedschaft': args['mv_mitgliedschaft'],
            'notiz': notiz,
            'raised_by': args['email'] if args['email'] else None,
            'telefon_privat_mobil': args['telefon'] if args['telefon'] else None,
            'anderes_mietobjekt': args['anderes_mietobjekt'] if args['anderes_mietobjekt'] else None,
            'frage': args['frage'] if args['frage'] else None,
            'datum_mietzinsanzeige': args['datum_mietzinsanzeige'] if args['datum_mietzinsanzeige'] else None
        })
        new_ber.insert(ignore_permissions=True)
        frappe.db.commit()
        if args['email']:
            sektion = frappe.db.get_value("Mitgliedschaft", args['mv_mitgliedschaft'], "sektion_id")
            send_confirmation_mail(args['mv_mitgliedschaft'], new_ber.name, notiz, raised_by=args['email'], sektion=sektion)
        
        return new_ber.name
    else:
        return 'error'

@frappe.whitelist(allow_guest=True)
def new_file_to_beratung(**kwargs):
    args = json.loads(kwargs['kwargs'])
    if frappe.db.exists("Beratung", args['beratung']):
        document_type = 'Sonstiges'
        man_document_type = None
        if args['document_type']:
            if args['document_type'] in [
                        'Mietvertrag',
                        'Mietzinserhöhung',
                        'Mietzinsherabsetzung',
                        'Vergleich/Urteil',
                        'Vereinbarung',
                        'sonstige Vertragsänderung'
                    ]:
                document_type = args['document_type']
            else:
                man_document_type = args['document_type']
        try:
            file_path = '/private/files/{0}'.format(args['filename'])
            new_file = frappe.get_doc({
                'doctype': 'Beratungsdateien',
                'parentfield': 'dokumente',
                'parenttype': 'Beratung',
                'parent': args['beratung'],
                'idx': args['idx'],
                'document_type': document_type,
                'man_document_type': man_document_type,
                'filename': args['filename'].replace(".pdf", "").replace(".jpg", "").replace(".jpeg", ""),
                'document_date': args['document_date'] if args['document_date'] else None,
                'file': file_path
            })
            new_file.insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error("{0}".format(str(e)), "File Upload fehlerhaft")
    else:
        frappe.log_error("{0}".format(args['beratung']), "File Upload unvollständig")

@frappe.whitelist(allow_guest=True)
def get_upload_keys():
    return {
        'key': frappe.db.get_value("MVD Settings", "MVD Settings", "upload_key"),
        'secret': frappe.db.get_value("MVD Settings", "MVD Settings", "upload_secret")
    }

def send_confirmation_mail(mitgliedschaft, beratung, notiz, raised_by=None, legacy_mail=False, sektion=None):
    if not legacy_mail:
        message = """Guten Tag"""
        if frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "vorname_1"):
            message += " {0}".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "vorname_1"))
        if frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "nachname_1"):
            message += " {0}".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "nachname_1"))
        message += """<br><br>Die untenstehende Frage ist bei uns eingetroffen.
                    <br><br><b>Mitgliedernummer</b>: {0}<br>{1}""".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "mitglied_nr"), notiz)
        message += """<br><br>Freundliche Grüsse<br>
                    Ihr Mieterinnen- und Mieterverband"""
        
        comm = make(
            recipients=[raised_by],
            sender=frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail"),
            subject='Vielen Dank für Ihre Anfrage', 
            content=message,
            doctype='Beratung',
            name=beratung,
            send_email=False,
            sender_full_name=frappe.get_value("Sektion", sektion, "legacy_mail_absende_name")
        )["name"]
        
        sendmail(
            recipients=[raised_by],
            sender="{0} <{1}>".format(frappe.get_value("Sektion", sektion, "legacy_mail_absende_name"), frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail")),
            subject='Vielen Dank für Ihre Anfrage', 
            message=message,
            as_markdown=False,
            delayed=True,
            reference_doctype='Beratung',
            reference_name=beratung,
            unsubscribe_method=None,
            unsubscribe_params=None,
            unsubscribe_message=None,
            attachments=[],
            content=None,
            doctype='Beratung',
            name=beratung,
            reply_to=frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail"),
            cc=[],
            bcc=[],
            message_id=frappe.get_value("Communication", comm, "message_id"),
            in_reply_to=None,
            send_after=None,
            expose_recipients=None,
            send_priority=1,
            communication=comm,
            retry=1,
            now=None,
            read_receipt=None,
            is_notification=False,
            inline_images=None,
            header=None,
            print_letterhead=False
        )
    else:
        try:
            message = False
            attachments = None
            if legacy_mail == '1':
                # legacy mail mit links
                message = """Guten Tag {0}""".format(sektion)
                message += """<br><br>Die untenstehende Frage ist bei uns eingetroffen.
                        <br><br><b>Mitgliedernummer</b>: {0}<br>{1}<br><br>Anhänge:<br>""".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "mitglied_nr"), notiz)
                for file_data in frappe.get_doc("Beratung", beratung).dokumente:
                    message += """<a href="{0}">{1}</a><br>""".format(get_url(file_data.file), file_data.filename)
                
                message += """<br>Freundliche Grüsse<br>
                            libracore"""
            
            elif legacy_mail == '2':
                # legacy mail mit anhängen
                message = """Guten Tag {0}""".format(sektion)
                message += """<br><br>Die untenstehende Frage ist bei uns eingetroffen.
                        <br><br><b>Mitgliedernummer</b>: {0}<br>{1}""".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "mitglied_nr"), notiz)
                message += """<br>Freundliche Grüsse<br>
                            libracore"""
                attachments = []
                all_attachments = frappe.db.sql("""SELECT `name` FROM `tabFile` WHERE `attached_to_doctype` = 'Beratung' AND `attached_to_name` = '{0}'""".format(beratung), as_dict=True)
                for f in all_attachments:
                    attachments.append({'fid': f.name})
            
            if message:
                recipient = frappe.db.get_value("Sektion", sektion, 'legacy_email')
                
                comm = make(
                    recipients=[recipient],
                    sender=frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail"),
                    subject='Neue E-Mail Beratung', 
                    content=message,
                    doctype='Beratung',
                    name=beratung,
                    send_email=False,
                    sender_full_name=frappe.get_value("Sektion", sektion, "legacy_mail_absende_name"),
                    attachments=attachments
                )["name"]
                
                sendmail(
                    recipients=[recipient],
                    sender="{0} <{1}>".format(frappe.get_value("Sektion", sektion, "legacy_mail_absende_name"), frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail")),
                    subject='Neue E-Mail Beratung', 
                    message=message,
                    as_markdown=False,
                    delayed=True,
                    reference_doctype='Beratung',
                    reference_name=beratung,
                    unsubscribe_method=None,
                    unsubscribe_params=None,
                    unsubscribe_message=None,
                    attachments=attachments,
                    content=None,
                    doctype='Beratung',
                    name=beratung,
                    reply_to=raised_by,
                    cc=[],
                    bcc=[],
                    message_id=frappe.get_value("Communication", comm, "message_id"),
                    in_reply_to=None,
                    send_after=None,
                    expose_recipients=None,
                    send_priority=1,
                    communication=comm,
                    retry=1,
                    now=None,
                    read_receipt=None,
                    is_notification=False,
                    inline_images=None,
                    header=None,
                    print_letterhead=False
                )
        except Exception as e:
            frappe.log_error("{0}".format(str(e)), "Legacy Mail failed")
        
    return

@frappe.whitelist(allow_guest=True)
def check_legacy_mode(**kwargs):
    args = json.loads(kwargs['kwargs'])
    mitgliedschaft_id = args['mv_mitgliedschaft']
    sektion = frappe.db.get_value("Mitgliedschaft", mitgliedschaft_id, 'sektion_id')
    if frappe.db.get_value("Sektion", sektion, 'legacy_mode') == '2':
        return True
    else:
        return False

@frappe.whitelist(allow_guest=True)
def send_legacy_mail(**kwargs):
    # legacy mail
    args = json.loads(kwargs['kwargs'])
    beratung = args['beratung']
    raised_by = args['raised_by']
    
    # mark for SP API
    frappe.db.set_value("Beratung", beratung, 'trigger_api', 1, update_modified=False)
    
    mitgliedschaft_id = frappe.db.get_value("Beratung", beratung, 'mv_mitgliedschaft')
    sektion = frappe.db.get_value("Mitgliedschaft", mitgliedschaft_id, 'sektion_id')
    notiz = frappe.db.get_value("Beratung", beratung, 'notiz')
    frappe.log_error("{0},\n{1},\n{2},\n{3},\n{4}".format(beratung, raised_by, mitgliedschaft_id, sektion, notiz), "Trigger Legacy Mail (OK)")
    if frappe.db.get_value("Sektion", sektion, 'legacy_mode') != '0':
        send_confirmation_mail(mitgliedschaft_id, beratung, notiz, legacy_mail=frappe.db.get_value("Sektion", sektion, 'legacy_mode'), sektion=sektion, raised_by=raised_by)
        return

def send_to_sp():
    beratungen = frappe.db.sql("""SELECT `name` FROM `tabBeratung` WHERE `trigger_api` = 1""", as_dict=True)
    for ber in beratungen:
        beratung = frappe.get_doc("Beratung", ber.name)
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", beratung.mv_mitgliedschaft)
        prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
        dokumente = []
        files = frappe.db.sql("""SELECT `name`, `file_name` FROM `tabFile` WHERE `attached_to_name` = '{0}'""".format(beratung.name), as_dict=True)
        for dok in files:
            dok_data = {
                "beratungDokumentId": dok.name,
                "name": dok.file_name,
                "datum": get_datetime_str(beratung.start_date).replace(" ", "T"),
                "typ": str(dok.file_name.split(".")[len(dok.file_name.split(".")) - 1])
            }
            dokumente.append(dok_data)
            
        json_to_send = {
            "beratungId": beratung.name,
            "mitglied": prepared_mvm,
            "datumEingang": get_datetime_str(beratung.start_date).replace(" ", "T"),
            # ~ "beratungskategorie": beratung.beratungskategorie,
            "beratungskategorie": 'Mietzinserhöhung' if beratung.datum_mietzinsanzeige else 'Allgemeine Anfrage',
            "telefonPrivatMobil": beratung.telefon_privat_mobil,
            "email": beratung.raised_by,
            "anderesMietobjekt": beratung.anderes_mietobjekt,
            "frage": beratung.frage,
            "datumBeginnFrist": get_datetime_str(beratung.start_date).replace(" ", "T"),
            "dokumente": dokumente
        }
        
        frappe.log_error("{0}".format(str(json_to_send)), "Beratung an SP gesendet (OK)")
        send_beratung(json_to_send)
        
        # remove mark for SP API
        frappe.db.set_value("Beratung", beratung.name, 'trigger_api', 0, update_modified=False)
