from __future__ import unicode_literals
import frappe
import json
import jwt

no_cache = 1

def get_context(context):
    context.show_sidebar = True
    authorization_header = frappe.get_request_header("Cookie", None)
    jwt_token = None
    
    if authorization_header:
        for cookie in authorization_header.split(";"):
            if cookie.startswith(" jwt_auth="):
                jwt_token = cookie.split(" jwt_auth=")[1]
    
    if jwt_token:
        public_key = frappe.db.get_single_value('JWT', 'public_key')
        algorythmus = frappe.db.get_single_value('JWT', 'algorythmus')
        decoded_jwt_token = jwt.decode(jwt_token, public_key, algorithms=[algorythmus])
        context.jwt_token = decoded_jwt_token
        if 'mitglied_id' in decoded_jwt_token:
            if frappe.db.exists("Mitgliedschaft", decoded_jwt_token["mitglied_id"]):
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", decoded_jwt_token["mitglied_id"])
                context = context_erweiterung(context, mitgliedschaft)
            else:
                raise_redirect()
        else:
            raise_redirect()
    else:
        raise_redirect()

def raise_redirect():
    frappe.local.flags.redirect_location = "/nologin"
    raise frappe.Redirect

def context_erweiterung(context, mitgliedschaft):
    return context

@frappe.whitelist(allow_guest=True)
def new_onlineberatung(**kwargs):
    args = json.loads(kwargs['kwargs'])
    if frappe.db.exists("Mitgliedschaft", args['mv_mitgliedschaft']):
        args['doctype'] = "Onlineberatung"
        new_ob = frappe.get_doc(args)
        new_ob.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.msgprint("Vielen Dank, die Anfrage wurde gespeichert.")
    else:
        frappe.throw("Die Mitgliedschaft {0} konnte nicht abgerufen werden".format(args['mv_mitgliedschaft']))
