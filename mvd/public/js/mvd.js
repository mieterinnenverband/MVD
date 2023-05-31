// Copyright (c) 2021-2022, libracore AG and contributors
// For license information, please see license.txt

// add links to MVD wiki
frappe.provide('frappe.help.help_links');
frappe.call({
    method: 'mvd.mvd.doctype.mv_help_links.mv_help_links.get_help_links',
    callback: function(r) {
        if(r.message) {
            var links = r.message;
            for (var i = 0; i < links.length; i++) {
                frappe.help.help_links['List/' + links[i].doctype_link] = [
                    { label: links[i].label, url: links[i].url },
                ];
                frappe.help.help_links['Form/' + links[i].doctype_link] = [
                    { label: links[i].label, url: links[i].url },
                ];
                frappe.help.help_links['Tree/' + links[i].doctype_link] = [
                    { label: links[i].label, url: links[i].url },
                ];
            }
        } 
    }
});

// Redirect to VBZ after login, reset user default and set navbar color to red if test
$(document).ready(function() {
    // reset user company default
    //frappe.defaults.set_user_default_local("Company", '');
    
    // mark navbar in specific colour
    setTimeout(function(){
        var navbars = document.getElementsByClassName("navbar");
        if (navbars.length > 0) {
            if ((window.location.hostname.includes("test-libracore")) || (window.location.hostname.includes("localhost")) || (window.location.hostname.includes("192.168.0.18")) || (window.location.hostname.includes("dev-libracore"))) {
                navbars[0].style.backgroundColor = "#B0473A";
            }
        }
    }, 2000);
    
    // redirect from desk to vbz
    if(frappe._cur_route==""||frappe._cur_route=="#") {
        window.location.href = "#vbz";
    }
    
    
});

// Redirect to VBZ after click on Navbar Desk Shortcut
$(document).on('click','#navbar-breadcrumbs a, a.navbar-home',function(event){
    event.preventDefault();
    var navURL = event.currentTarget.href;
    if(navURL.endsWith("#")) {
        if (frappe._cur_route != "#vbz") {
            navURL += "vbz";
        } else {
            navURL = frappe._cur_route
        }
    }
    if (!!cur_frm) {
        if (['Mitgliedschaft', 'Termin'].includes(cur_frm.doctype)) {
            if (cur_frm.is_dirty()&&frappe._cur_route.includes("Form")) {
                var confirm_message = 'Diese Mitgliedschaft besitzt ungespeicherte Änderungen,<br>möchten Sie die Mitgliedschaft trotzdem verlassen?';
                if (cur_frm.doctype == "Termin") {
                    confirm_message = 'Dieser Termin besitzt ungespeicherte Änderungen,<br>möchten Sie den Termin trotzdem verlassen?';
                }
                frappe.confirm(confirm_message,
                () => {
                    if(navURL.endsWith("vbz")) {
                        if (frappe._cur_route != "#vbz") {
                            frappe.dom.freeze('Lade Verarbeitungszentrale...');
                        }
                        window.location.href = navURL;
                    } else {
                        window.location.href = navURL;
                    }
                }, () => {
                    // No
                })
            } else {
                if(navURL.endsWith("vbz")) {
                    if (frappe._cur_route != "#vbz") {
                        frappe.dom.freeze('Lade Verarbeitungszentrale...');
                    }
                    window.location.href = navURL;
                } else {
                    window.location.href = navURL;
                }
            }
        }  else {
                if(navURL.endsWith("vbz")) {
                    if (frappe._cur_route != "#vbz") {
                        frappe.dom.freeze('Lade Verarbeitungszentrale...');
                    }
                    window.location.href = navURL;
                } else {
                    window.location.href = navURL;
                }
        }
    } else {
        if(navURL.endsWith("vbz")) {
            if (frappe._cur_route != "#vbz") {
                    frappe.dom.freeze('Lade Verarbeitungszentrale...');
                }
            window.location.href = navURL;
        } else {
            window.location.href = navURL;
        }
    }
});

window.onload = function() {
    window.addEventListener("beforeunload", function (e) {
        if (!!cur_frm) {
            if (['Mitgliedschaft', 'Termin'].includes(cur_frm.doctype)) {
                if (!cur_frm.is_dirty()) {
                    return undefined;
                }

                var confirmationMessage = 'It looks like you have been editing something. '
                                        + 'If you leave before saving, your changes will be lost.';
                
                (e || window.event).returnValue = confirmationMessage; //Gecko + IE
                return confirmationMessage; //Gecko + Webkit, Safari, Chrome etc.
            } else {
                return undefined;
            }
        }
    });
};

$(document).on("page-change", function() {
    if (window.location.hash.includes('#Form/Beratung/')) {
        // Funktion zum gewährleisten, dass die Beratung beim öffnen ohne onload-Trigger gesperrt wird
        var beratung = window.location.hash.split("/")[window.location.hash.split("/").length - 1]
        frappe.db.get_value("Beratung", beratung, 'gesperrt_am')
            .then(({ message }) => {
                    var gesperrt_am = message.gesperrt_am
                    if (!gesperrt_am) {
                        cur_frm.reload_doc();
                    } else {
                        // Funktion zum gewährleisten, dass die Beratung beim öffnen ohne onload-Trigger neugeladen wird wenn sie gesperrt ist
                        frappe.db.get_value("Beratung", beratung, 'gesperrt_von')
                            .then(({ message }) => {
                                    gesperrt_von = message.gesperrt_von
                                    if ((gesperrt_von != frappe.session.user)&&(gesperrt_am != cur_frm.doc.gesperrt_am)) {
                                        cur_frm.reload_doc();
                                    }
                                });
                    }
                });
    } else {
        // Funktion zum gewährleisten, dass die Beratung beim verlassen freigegeben wird
        if (frappe.route_history.length >= 2) {
            if (frappe.route_history[frappe.route_history.length - 2]) {
                if (frappe.route_history[frappe.route_history.length - 2][0] == 'Form') {
                    if (frappe.route_history[frappe.route_history.length - 2][1] == 'Beratung') {
                        frappe.call({
                            method: "mvd.mvd.doctype.beratung.beratung.clear_protection",
                            args:{
                                    'beratung': frappe.route_history[frappe.route_history.length - 2][2]
                            }
                        });
                    }
                } else if (frappe.route_history.length >= 3) {
                    if (frappe.route_history[frappe.route_history.length - 3][0] == 'Form') {
                        if (frappe.route_history[frappe.route_history.length - 3][1] == 'Beratung') {
                            frappe.call({
                                method: "mvd.mvd.doctype.beratung.beratung.clear_protection",
                                args:{
                                        'beratung': frappe.route_history[frappe.route_history.length - 3][2]
                                }
                            });
                        }
                    }
                }
            }
        }
    }
});
