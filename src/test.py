i am working on a django-rest-framwwork ecommerce project , i need to add some analysis ApiViews endpoints to use them in the dashboard as following :
1 - an endpoint to get low threshold products to warn the admin .
2 - an endpoint to get the sales and can be filtered by start and end date and also can be filtered for a specific product or a specific category , an example json rsponse is  :
{
     "total_paid_items_price": 15000.0, // already paid items
     "total_paid_items_native_price": 5000.0,
    "total_paid_items_revenue": 10000.0,
"total_paid_items_pieces": 50,
"total_unpaid_items_price": 15000.0, // already pilled but paid yet (pills with status = "p")
     "total_unpaid_items_native_price": 5000.0,
    "total_unpaid_items_expected_revenue": 1000.0,
"total_unpaid_items_pieces": 40,
    "product_sales_details": [ // i put any numbers but in real the totals of the specific products should be equals the full total of the upove general totals .
        {
            "product__name": "prod1",
            "product__id": 1,
            "total_paid_items_price": 10000.0, // already paid items
     "total_paid_items_native_price": 3000.0,
    "total_paid_items_revenue": 5000.0,
"total_paid_items_pieces": 50,
"total_unpaid_items_price": 15000.0, // already pilled but paid yet (pills with status = "p")
     "total_unpaid_items_native_price": 5000.0,
    "total_unpaid_items_expected_revenue": 1000.0,
"total_unpaid_items_pieces": 40,
        },
        {
            "product__name": "prod2",
            "product__id": 2,
             "total_paid_items_price": 15000.0, // already paid items
     "total_paid_items_native_price": 5000.0,
    "total_paid_items_revenue": 1000.0,
"total_paid_items_pieces": 50,
"total_unpaid_items_price": 15000.0, // already pilled but paid yet (pills with status = "p")
     "total_unpaid_items_native_price": 5000.0,
    "total_unpaid_items_expected_revenue": 1000.0,
"total_unpaid_items_pieces": 40,
        }
    ]
}

3 - total count of pills and total count of each status of the pills (as 3 waiting pills , 5 paid pills , 10 delivered pills, ...)
4 - total loved items of all product (how many times that product loved) and able to be ordered desc and ascend 