"""Email delivery service used by authentication flows."""

from email.message import EmailMessage
from html import escape
import smtplib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.configs.configs import settings


class EmailService:
    """Service for sending transactional emails through a configurable SMTP server."""

    @staticmethod
    def _normalize_single_recipient(recipient) -> str:
        """Accept only one recipient per email message."""
        if isinstance(recipient, (list, tuple, set, frozenset)):
            raise RuntimeError(
                "Email delivery accepts only one recipient per message."
            )

        normalized = str(recipient or "").strip()
        if not normalized:
            raise RuntimeError("Recipient email is required.")

        if "," in normalized or ";" in normalized:
            raise RuntimeError(
                "Email delivery accepts only one recipient per message."
            )

        return normalized

    @staticmethod
    def _get_smtp_delivery_settings(require_enabled: bool = False) -> dict | None:
        """Load and validate SMTP settings used by email delivery flows."""
        smtp_enabled = EmailService._get_setting("SMTP_ENABLED", False)
        smtp_host = EmailService._normalize_smtp_value(
            EmailService._get_setting("SMTP_HOST")
        )
        smtp_port = EmailService._get_setting("SMTP_PORT", 587)
        smtp_username = EmailService._normalize_smtp_value(
            EmailService._get_setting("SMTP_USERNAME")
        )
        smtp_password = EmailService._normalize_smtp_value(
            EmailService._get_setting("SMTP_PASSWORD")
        )
        smtp_use_tls = EmailService._get_setting("SMTP_USE_TLS", True)
        smtp_use_ssl = EmailService._get_setting("SMTP_USE_SSL", False)
        smtp_from_email = EmailService._normalize_smtp_value(
            EmailService._get_setting("SMTP_FROM_EMAIL")
        )

        if not smtp_enabled:
            if require_enabled:
                raise RuntimeError(
                    "SMTP delivery is disabled. Enable SMTP_ENABLED before sending emails."
                )
            return None

        if not smtp_host or not smtp_from_email:
            raise RuntimeError(
                "SMTP is enabled but SMTP_HOST/SMTP_FROM_EMAIL are not fully configured."
            )

        if smtp_host.lower() == "smtp.gmail.com":
            if smtp_password:
                # Google app passwords are displayed in grouped blocks, but SMTP
                # authentication expects the underlying token value.
                smtp_password = smtp_password.replace(" ", "")

            if not smtp_username or not smtp_password:
                raise RuntimeError(
                    "SMTP_USERNAME/SMTP_PASSWORD must be configured when using smtp.gmail.com."
                )

        if smtp_host.lower() == "smtp.gmail.com" and (
            len(smtp_password or "") != 16
        ):
            raise RuntimeError(
                "SMTP_PASSWORD for smtp.gmail.com must be a 16-character Google app password."
            )

        return {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_username": smtp_username,
            "smtp_password": smtp_password,
            "smtp_use_tls": smtp_use_tls,
            "smtp_use_ssl": smtp_use_ssl,
        }

    @staticmethod
    def _get_setting(name: str, default=None):
        """Safely read optional settings attributes with a fallback."""
        return getattr(settings, name, default)

    @staticmethod
    def _normalize_smtp_value(value: str | None) -> str | None:
        """Trim whitespace and optional wrapping quotes from SMTP settings."""
        if value is None:
            return None

        normalized = value.strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1]:
            if normalized[0] in {'"', "'"}:
                normalized = normalized[1:-1].strip()

        return normalized

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
        recipient = EmailService._normalize_single_recipient(recipient)
        smtp_from_email = EmailService._get_setting("SMTP_FROM_EMAIL")
        smtp_from_name = EmailService._get_setting("SMTP_FROM_NAME", "UBA Questionary")
        reset_expiration_minutes = EmailService._get_setting(
            "PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES", 30
        )

        if not smtp_from_email:
            raise RuntimeError(
                "SMTP_FROM_EMAIL must be configured when SMTP is enabled."
            )

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
    def _build_inactive_plan_follow_up_message(
        recipient: str,
        recipient_name: str | None,
        subject: str,
        body: str,
    ) -> EmailMessage:
        """Build the manual outreach email for users without an active plan."""
        recipient = EmailService._normalize_single_recipient(recipient)
        smtp_from_email = EmailService._get_setting("SMTP_FROM_EMAIL")
        smtp_from_name = EmailService._get_setting("SMTP_FROM_NAME", "UBA Questionary")
        support_email = EmailService._normalize_smtp_value(
            EmailService._get_setting("SUPPORT_EMAIL")
        ) or smtp_from_email

        if not smtp_from_email:
            raise RuntimeError(
                "SMTP_FROM_EMAIL must be configured when SMTP is enabled."
            )

        greeting_name = (recipient_name or "").strip()
        greeting = f"Ola, {escape(greeting_name)}!" if greeting_name else "Ola!"
        formatted_body = "<br>".join(escape(body).splitlines())

        html_body = (
            "<html><body>"
            f"<p>{greeting}</p>"
            f"<p>{formatted_body}</p>"
            "<p>Se quiser, e so responder este email contando o que esta faltando "
            "ou o que te impediria de voltar a usar a plataforma.</p>"
            "<p>Obrigado!</p>"
            "</body></html>"
        )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{smtp_from_name} <{smtp_from_email}>"
        message["To"] = recipient
        message["Reply-To"] = support_email
        message.set_content(html_body, subtype="html")

        return message

    @staticmethod
    def _send_message(message: EmailMessage, require_enabled: bool = False) -> None:
        """Deliver a prepared email message via SMTP."""
        delivery_settings = EmailService._get_smtp_delivery_settings(
            require_enabled=require_enabled
        )
        if delivery_settings is None:
            return

        smtp = None

        try:
            smtp_class = (
                smtplib.SMTP_SSL
                if delivery_settings["smtp_use_ssl"]
                else smtplib.SMTP
            )
            smtp = smtp_class(
                delivery_settings["smtp_host"],
                delivery_settings["smtp_port"],
                timeout=30,
            )
            smtp.ehlo()

            if (
                delivery_settings["smtp_use_tls"]
                and not delivery_settings["smtp_use_ssl"]
            ):
                smtp.starttls()
                smtp.ehlo()

            if (
                delivery_settings["smtp_username"]
                and delivery_settings["smtp_password"]
            ):
                smtp.login(
                    delivery_settings["smtp_username"],
                    delivery_settings["smtp_password"],
                )

            smtp.send_message(message)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise RuntimeError("Unable to send email.") from exc
        finally:
            if smtp is not None:
                try:
                    smtp.quit()
                except smtplib.SMTPServerDisconnected:
                    pass

    @staticmethod
    def send_password_reset_email(recipient: str, reset_token: str) -> None:
        """Send a password reset email when SMTP delivery is enabled."""
        message = EmailService._build_password_reset_message(recipient, reset_token)

        try:
            EmailService._send_message(message)
        except RuntimeError as exc:
            raise RuntimeError("Unable to send password reset email.") from exc

    @staticmethod
    def send_inactive_plan_follow_up_email(
        recipient: str,
        recipient_name: str | None,
        subject: str,
        body: str,
    ) -> None:
        """Send a manual outreach email to a user without an active plan."""
        message = EmailService._build_inactive_plan_follow_up_message(
            recipient=recipient,
            recipient_name=recipient_name,
            subject=subject,
            body=body,
        )
        try:
            EmailService._send_message(message, require_enabled=True)
        except RuntimeError as exc:
            raise RuntimeError("Unable to send inactive-plan follow-up email.") from exc
