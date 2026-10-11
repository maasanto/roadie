def keep_invitee_in_roadie(invitation, method=None):
	"""invite_by_email takes the page to land on from the client, so a member could send an invitee off-site."""
	if invitation.app_name == "roadie":
		invitation.redirect_to_path = "/roadie"
