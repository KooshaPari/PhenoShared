package domain

import (
	"testing"
)

func TestNewEmail(t *testing.T) {
	tests := []struct {
		name    string
		address string
		wantErr bool
	}{
		{"valid email", "test@example.com", false},
		{"valid with subdomain", "user@mail.example.com", false},
		{"valid with plus", "user+tag@example.com", false},
		{"invalid no at", "testexample.com", true},
		{"invalid no domain", "test@", true},
		{"invalid no local", "@example.com", true},
		{"invalid spaces", "test @example.com", true},
		{"empty", "", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			email, err := NewEmail(tt.address)

			if tt.wantErr {
				if err == nil {
					t.Error("expected error, got nil")
				}
			} else {
				if err != nil {
					t.Errorf("expected no error, got %v", err)
				}
				if email != nil && email.String() != tt.address {
					t.Errorf("expected %s, got %s", tt.address, email.String())
				}
			}
		})
	}
}

func TestNewEmail_Lowercase(t *testing.T) {
	email, err := NewEmail("TEST@EXAMPLE.COM")

	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if email.String() != "test@example.com" {
		t.Errorf("expected lowercase, got %s", email.String())
	}
}

func TestMustNewEmail_Panic(t *testing.T) {
	defer func() {
		if r := recover(); r == nil {
			t.Error("expected panic for invalid email")
		}
	}()

	MustNewEmail("invalid")
}

func TestNewNonEmptyString(t *testing.T) {
	tests := []struct {
		name  string
		value string
		want  string
	}{
		{"normal string", "hello", "hello"},
		{"with spaces", "  hello  ", "  hello  "},
		{"single word", "word", "word"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			vo, err := NewNonEmptyString(tt.value)

			if err != nil {
				t.Errorf("expected no error, got %v", err)
			}
			if vo.String() != tt.want {
				t.Errorf("expected %s, got %s", tt.want, vo.String())
			}
		})
	}
}

func TestNewNonEmptyString_Empty(t *testing.T) {
	tests := []string{"", "   ", "\t", "\n"}

	for _, v := range tests {
		_, err := NewNonEmptyString(v)
		if err == nil {
			t.Errorf("expected error for empty string '%q'", v)
		}
	}
}

func TestMustNewNonEmptyString_Panic(t *testing.T) {
	defer func() {
		if r := recover(); r == nil {
			t.Error("expected panic for empty string")
		}
	}()

	MustNewNonEmptyString("")
}

func TestValueObject_Equals(t *testing.T) {
	email1, _ := NewEmail("test@example.com")
	email2, _ := NewEmail("test@example.com")
	email3, _ := NewEmail("other@example.com")

	if !email1.Equals(email2) {
		t.Error("expected equal emails to be equal")
	}

	if email1.Equals(email3) {
		t.Error("expected different emails to not be equal")
	}

	if email1.Equals(nil) {
		t.Error("expected nil comparison to return false")
	}
}

func TestMoney(t *testing.T) {
	money := NewMoney(1000, "USD")

	if money.Amount() != 1000 {
		t.Errorf("expected 1000, got %d", money.Amount())
	}

	if money.Currency() != "USD" {
		t.Errorf("expected USD, got %s", money.Currency())
	}
}

func TestMoney_CurrencyUppercase(t *testing.T) {
	money := NewMoney(100, "usd")

	if money.Currency() != "USD" {
		t.Errorf("expected USD (uppercase), got %s", money.Currency())
	}
}

func TestMoney_String(t *testing.T) {
	money := NewMoney(1999, "USD")

	if money.String() != "USD 19.99" {
		t.Errorf("expected 'USD 19.99', got '%s'", money.String())
	}
}

func TestMoney_Equals(t *testing.T) {
	m1 := NewMoney(100, "USD")
	m2 := NewMoney(100, "USD")
	m3 := NewMoney(100, "EUR")
	m4 := NewMoney(200, "USD")

	if !m1.Equals(m2) {
		t.Error("expected equal money to be equal")
	}

	if m1.Equals(m3) {
		t.Error("expected different currencies to not be equal")
	}

	if m1.Equals(m4) {
		t.Error("expected different amounts to not be equal")
	}

	if m1.Equals(nil) {
		t.Error("expected nil comparison to return false")
	}
}
