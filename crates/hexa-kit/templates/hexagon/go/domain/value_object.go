package domain

import (
	"fmt"
	"regexp"
	"strings"
)

// ValueObject is the interface that all value objects implement
// Value objects are immutable and compared by value, not identity
type ValueObject interface {
	Equals(ValueObject) bool
	String() string
}

// BaseValueObject provides common value object functionality
type BaseValueObject struct {
	value string
}

// NewBaseValueObject creates a new base value object
func NewBaseValueObject(value string) *BaseValueObject {
	return &BaseValueObject{value: value}
}

// String returns the string representation
func (v *BaseValueObject) String() string {
	return v.value
}

// Equals checks if two value objects are equal
func (v *BaseValueObject) Equals(other ValueObject) bool {
	if other == nil {
		return false
	}
	return v.String() == other.String()
}

// Email is a value object for email addresses
type Email struct {
	BaseValueObject
}

// NewEmail creates a new email value object
func NewEmail(address string) (*Email, error) {
	email := regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)
	if !email.MatchString(address) {
		return nil, fmt.Errorf("%w: invalid email format", ErrInvalidInput)
	}
	return &Email{BaseValueObject{value: strings.ToLower(address)}}, nil
}

// MustNewEmail creates a new email or panics
func MustNewEmail(address string) *Email {
	email, err := NewEmail(address)
	if err != nil {
		panic(err)
	}
	return email
}

// NonEmptyString is a value object that ensures non-empty strings
type NonEmptyString struct {
	BaseValueObject
}

// NewNonEmptyString creates a new non-empty string value object
func NewNonEmptyString(value string) (*NonEmptyString, error) {
	if strings.TrimSpace(value) == "" {
		return nil, fmt.Errorf("%w: string cannot be empty", ErrInvalidInput)
	}
	return &NonEmptyString{BaseValueObject{value: value}}, nil
}

// MustNewNonEmptyString creates a new non-empty string or panics
func MustNewNonEmptyString(value string) *NonEmptyString {
	s, err := NewNonEmptyString(value)
	if err != nil {
		panic(err)
	}
	return s
}

// Money represents a monetary value
type Money struct {
	amount   int64 // stored in cents
	currency string
}

// NewMoney creates a new money value object
func NewMoney(amount int64, currency string) *Money {
	return &Money{
		amount:   amount,
		currency: strings.ToUpper(currency),
	}
}

// Amount returns the amount in cents
func (m *Money) Amount() int64 {
	return m.amount
}

// Currency returns the currency code
func (m *Money) Currency() string {
	return m.currency
}

// String returns the formatted money string
func (m *Money) String() string {
	return fmt.Sprintf("%s %.2f", m.currency, float64(m.amount)/100)
}

// Equals checks if two money values are equal
func (m *Money) Equals(other ValueObject) bool {
	money, ok := other.(*Money)
	if !ok {
		return false
	}
	return m.amount == money.amount && m.currency == money.currency
}
