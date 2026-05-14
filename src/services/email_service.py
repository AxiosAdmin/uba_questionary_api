"""Email delivery service used by authentication flows."""

from email.message import EmailMessage
import smtplib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.configs.configs import settings


class EmailService:
    """Service for sending transactional emails through a configurable SMTP server."""

    @staticmethod
    def _get_setting(name: str, default=None):
        """Safely read optional settings attributes with a fallback."""
        return getattr(settings, name, default)

    @staticmethod
    def _build_password_reset_destination(reset_token: str) -> str:
        password_reset_url = EmailService._get_setting("PASSWORD_RESET_URL")
        if password_reset_url:
            parts = urlsplit(password_reset_url)
            query_items = dict(parse_qsl(parts.query, keep_blank_values=True))
            query_items["token"] = reset_token
            updated_query = urlencode(query_items)
            return urlunsplit(
                (parts.scheme, parts.netloc, parts.path, updated_query, parts.fragment)
            )

        return reset_token

    @staticmethod
    def _build_password_reset_message(recipient: str, reset_token: str) -> EmailMessage:
        smtp_from_email = EmailService._get_setting("SMTP_FROM_EMAIL")
        smtp_from_name = EmailService._get_setting("SMTP_FROM_NAME", "UBA Questionary")
        reset_expiration_minutes = EmailService._get_setting(
            "PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES", 30
        )

        if not smtp_from_email:
            raise RuntimeError("SMTP_FROM_EMAIL must be configured when SMTP is enabled.")

        destination = EmailService._build_password_reset_destination(reset_token)

        html_body = (
            "<html><body>"
            "<p>Ola,</p>"
            "<p>Recebemos uma solicitacao para redefinir sua senha.</p>"
            "<p>"
            f'Clique no <a href="{destination}">link de redefinicao de senha</a> '
            "para continuar."
            "</p>"
            f"<p>Este acesso expira em {reset_expiration_minutes} minutos.</p>"
            "<p>Se voce nao solicitou a redefinicao, ignore este e-mail.</p>"
            "</body></html>"
        )

        message = EmailMessage()
        message["Subject"] = "Redefinicao de senha"
        message["From"] = f"{smtp_from_name} <{smtp_from_email}>"
        message["To"] = recipient
        message.set_content(html_body, subtype="html")

        return message

    @staticmethod
    def send_password_reset_email(recipient: str, reset_token: str) -> None:
        """Send a password reset email when SMTP delivery is enabled."""
        smtp_enabled = EmailService._get_setting("SMTP_ENABLED", False)
        smtp_host = EmailService._get_setting("SMTP_HOST")
        smtp_port = EmailService._get_setting("SMTP_PORT", 587)
        smtp_username = EmailService._get_setting("SMTP_USERNAME")
        smtp_password = EmailService._get_setting("SMTP_PASSWORD")
        smtp_use_tls = EmailService._get_setting("SMTP_USE_TLS", True)
        smtp_use_ssl = EmailService._get_setting("SMTP_USE_SSL", False)
        smtp_from_email = EmailService._get_setting("SMTP_FROM_EMAIL")

        if not smtp_enabled:
            return

        if not smtp_host or not smtp_from_email:
            raise RuntimeError(
                "SMTP is enabled but SMTP_HOST/SMTP_FROM_EMAIL are not fully configured."
            )

        message = EmailService._build_password_reset_message(recipient, reset_token)

        smtp_class = smtplib.SMTP_SSL if smtp_use_ssl else smtplib.SMTP
        smtp = smtp_class(smtp_host, smtp_port, timeout=30)

        try:
            smtp.ehlo()

            if smtp_use_tls and not smtp_use_ssl:
                smtp.starttls()
                smtp.ehlo()

            if smtp_username and smtp_password:
                smtp.login(smtp_username, smtp_password)

            smtp.send_message(message)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise RuntimeError("Unable to send password reset email.") from exc
        finally:
            smtp.quit()
