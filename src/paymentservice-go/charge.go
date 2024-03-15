package main

import (
	"fmt"
	"github.com/google/uuid"
	pb "hipstershop"
	"regexp"
	"strconv"
	"strings"
	"time"
)

var cards = map[string]*regexp.Regexp{
	"amex":       regexp.MustCompile(`^3[47][0-9]{13}$`),
	"dinersclub": regexp.MustCompile(`^3(?:0[0-5]|[68][0-9])[0-9]{11}$`),
	"discover":   regexp.MustCompile(`^6(?:011|5[0-9][0-9])[0-9]{12,15}$`),
	"jcb":        regexp.MustCompile(`^(?:2131|1800|35\d{3})\d{11}$`),
	"mastercard": regexp.MustCompile(`^5[1-5][0-9]{2}|(222[1-9]|22[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}$`),
	"unionpay":   regexp.MustCompile(`^(6[27][0-9]{14}|^(81[0-9]{14,17}))$`),
	"visa":       regexp.MustCompile(`^(?:4[0-9]{12})(?:[0-9]{3,6})?$`),
}

// isCreditCard 函数用于验证信用卡号是否有效。
func isCreditCard(card string) (bool, string) {
	// 去除字符串中的连字符和空格，以便于后续处理
	sanitized := strings.ReplaceAll(card, "-", "")
	sanitized = strings.ReplaceAll(sanitized, " ", "")

	// 尝试使用所有预定义的正则表达式进行匹配
	for cardType, regex := range cards {
		if regex.MatchString(sanitized) {
			// 如果信用卡号与任何一个预定义的正则表达式匹配成功，使用 Luhn 算法验证信用卡号的校验位，以确保最后一位校验码有效
			return isLuhnValid(sanitized), cardType
		}
	}
	// 如果未匹配任何预定义的正则表达式，则返回 false 表示信用卡号无效
	return false, "unknown"
}

func isLuhnValid(sanitized string) bool {
	sum := 0
	shouldDouble := false
	for i := len(sanitized) - 1; i >= 0; i-- {
		digit := sanitized[i : i+1]
		tmpNum, _ := strconv.Atoi(digit)
		if shouldDouble {
			tmpNum *= 2
			if tmpNum >= 10 {
				sum += (tmpNum % 10) + 1
			} else {
				sum += tmpNum
			}
		} else {
			sum += tmpNum
		}
		shouldDouble = !shouldDouble
	}
	return sum%10 == 0
}

// ChargeHandler 处理支付请求
func ChargeHandler(request *pb.ChargeRequest) (*pb.ChargeResponse, error) {
	// 获取信用卡信息
	creditCard := request.CreditCard

	// 检查信用卡有效性
	valid, cardType := isCreditCard(creditCard.CreditCardNumber)
	if !valid {
		return nil, NewInvalidCreditCard()
	}

	// 检查信用卡类型
	if cardType != "visa" && cardType != "mastercard" {
		return nil, NewUnacceptedCreditCard(cardType)
	}

	// 检查信用卡是否过期
	currentMonth := time.Now().Month()
	currentYear := time.Now().Year()
	if creditCard.CreditCardExpirationYear < int32(currentYear) ||
		(creditCard.CreditCardExpirationYear == int32(currentYear) &&
			creditCard.CreditCardExpirationMonth < int32(currentMonth)) {
		return nil, NewExpiredCreditCard(creditCard.CreditCardNumber, creditCard.CreditCardExpirationMonth,
			creditCard.CreditCardExpirationYear)
	}

	// 生成随机的交易ID（UUID v4）
	transactionID := uuid.New().String()

	// 构造要插入 MongoDB 的数据
	transaction := Transaction{
		CreditCardNumber:          creditCard.CreditCardNumber,
		CreditCardType:            cardType,
		CreditCardExpirationYear:  creditCard.CreditCardExpirationYear,
		CreditCardExpirationMonth: creditCard.CreditCardExpirationMonth,
		TransactionID:             transactionID,
		TransactionAmount: &Money{
			CurrencyCode: request.Amount.CurrencyCode,
			Units:        request.Amount.Units,
			Nanos:        request.Amount.Nanos,
		},
		Timestamp: time.Now(),
	}

	// 将数据插入 MongoDB
	if err := collection.Insert(transaction); err != nil {
		log.Printf("Error inserting data into MongoDB: %v", err)
		return nil, err
	}

	// test
	//readAndPrintDataFromDB()

	// 返回交易ID
	return &pb.ChargeResponse{TransactionId: transactionID}, nil
}

// CreditCardError 表示信用卡错误
type CreditCardError struct {
	Message string
	Code    int
}

// Error 实现 error 接口中的 Error() 方法
func (e *CreditCardError) Error() string {
	return e.Message
}

// NewCreditCardError 创建新的信用卡错误
func NewCreditCardError(message string) *CreditCardError {
	return &CreditCardError{
		Message: message,
		Code:    400,
	}
}

// InvalidCreditCard 表示无效的信用卡错误
type InvalidCreditCard struct {
	*CreditCardError
}

// NewInvalidCreditCard 创建新的无效的信用卡错误
func NewInvalidCreditCard() *InvalidCreditCard {
	return &InvalidCreditCard{
		CreditCardError: NewCreditCardError("Credit card info is invalid"),
	}
}

// UnacceptedCreditCard 表示不被接受的信用卡错误
type UnacceptedCreditCard struct {
	*CreditCardError
}

// NewUnacceptedCreditCard 创建新的不被接受的信用卡错误
func NewUnacceptedCreditCard(cardType string) *UnacceptedCreditCard {
	message := fmt.Sprintf("Sorry, we cannot process %s credit cards. Only VISA or MasterCard is accepted.", cardType)
	return &UnacceptedCreditCard{
		CreditCardError: NewCreditCardError(message),
	}
}

// ExpiredCreditCard 表示信用卡过期错误
type ExpiredCreditCard struct {
	*CreditCardError
}

// NewExpiredCreditCard 创建新的信用卡过期错误
func NewExpiredCreditCard(number string, month int32, year int32) *ExpiredCreditCard {
	message := fmt.Sprintf("Your credit card (ending %s) expired on %d/%d", number[len(number)-4:], month, year)
	return &ExpiredCreditCard{
		CreditCardError: NewCreditCardError(message),
	}
}
