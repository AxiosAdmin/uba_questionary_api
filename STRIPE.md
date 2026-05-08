stripe trigger invoice.payment_succeeded
stripe trigger checkout.session.completed
stripe trigger invoice.payment_failed
stripe trigger customer.subscription.deleted

/stripe/generate
Response format
```{
  "adaptive_pricing": {
    "enabled": true
  },
  "after_expiration": null,
  "allow_promotion_codes": null,
  "amount_subtotal": 3000000,
  "amount_total": 3000000,
  "automatic_tax": {
    "enabled": false,
    "liability": null,
    "provider": null,
    "status": null
  },
  "billing_address_collection": null,
  "branding_settings": {
    "background_color": "#ffffff",
    "border_style": "rounded",
    "button_color": "#0074d4",
    "display_name": "\u00c1rea restrita de New business",
    "font_family": "default",
    "icon": null,
    "logo": null
  },
  "cancel_url": null,
  "client_reference_id": null,
  "client_secret": null,
  "collected_information": null,
  "consent": null,
  "consent_collection": null,
  "created": 1777992098,
  "currency": "ars",
  "currency_conversion": null,
  "custom_fields": [],
  "custom_text": {
    "after_submit": null,
    "shipping_address": null,
    "submit": null,
    "terms_of_service_acceptance": null
  },
  "customer": null,
  "customer_account": null,
  "customer_creation": "always",
  "customer_details": null,
  "customer_email": null,
  "discounts": [],
  "expires_at": 1778078498,
  "id": "cs_test_a1tJLTm5XEIi3hZ3ew39GjGjyALUf7pz8xSmjcb4iNtk3J0m8GEslj3XpJ",
  "integration_identifier": null,
  "invoice": null,
  "invoice_creation": null,
  "livemode": false,
  "locale": null,
  "managed_payments": {
    "enabled": false
  },
  "metadata": {},
  "mode": "subscription",
  "object": "checkout.session",
  "origin_context": null,
  "payment_intent": null,
  "payment_link": null,
  "payment_method_collection": "always",
  "payment_method_configuration_details": {
    "id": "pmc_1TRKnVQ0ygO3vjZJR2ZSuZO3",
    "parent": null
  },
  "payment_method_options": {
    "card": {
      "request_three_d_secure": "automatic"
    }
  },
  "payment_method_types": [
    "card"
  ],
  "payment_status": "unpaid",
  "permissions": null,
  "phone_number_collection": {
    "enabled": false
  },
  "recovered_from": null,
  "saved_payment_method_options": {
    "allow_redisplay_filters": [
      "always"
    ],
    "payment_method_remove": "disabled",
    "payment_method_save": null
  },
  "setup_intent": null,
  "shipping_address_collection": null,
  "shipping_cost": null,
  "shipping_options": [],
  "status": "open",
  "submit_type": null,
  "subscription": null,
  "success_url": "https://www.urlparaaguardarpagamento.com.br",
  "total_details": {
    "amount_discount": 0,
    "amount_shipping": 0,
    "amount_tax": 0
  },
  "ui_mode": "hosted_page",
  "url": "https://checkout.stripe.com/c/pay/cs_test_a1tJLTm5XEIi3hZ3ew39GjGjyALUf7pz8xSmjcb4iNtk3J0m8GEslj3XpJ#fidnandhYHdWcXxpYCc%2FJ2FgY2RwaXEnKSdicGRmZGhqaWBTZHdsZGtxJz8nZmprcXdqaScpJ2R1bE5gfCc%2FJ3VuWnFgdnFaMDRRV05oclQ1fGJKNnNvX09TN3R0dklIXWhQSU80bmIzdERvUT1VaT1GbGtKM2FpQF89Q3BjajVEd1w1Tl1SQmw3MXFyQm1KU0Z2T39hZzI8Q190Zk1cd0w1NUhxY1FKQGR0JyknY3dqaFZgd3Ngdyc%2FcXdwYCknZ2RmbmJ3anBrYUZqaWp3Jz8nJmNjY2NjYycpJ2lkfGpwcVF8dWAnPyd2bGtiaWBabHFgaCcpJ2BrZGdpYFVpZGZgbWppYWB3dic%2FcXdwYHgl",
  "wallet_options": null
}```