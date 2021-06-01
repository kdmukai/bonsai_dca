import datetime
import time

from models import APICredential, DCASchedule, Order
from exchanges.gemini import GeminiExchange, GeminiRequestException



def timer_thread():
    while True:
        print("Checking DCASchedules")
        for schedule in DCASchedule.select().where(DCASchedule.is_paused == False):
            if schedule.is_time_to_run:
                print(f"Running Schedule {schedule.id} {schedule.market_name}")
                schedule.last_run = datetime.datetime.now()
                schedule.save()

                if schedule.credential.exchange == APICredential.EXCHANGE__GEMINI:
                    exchange = GeminiExchange(schedule.credential)                    
                else:
                    raise Exception(f"Exchange {schedule.exchange} not implemented yet!")

                order = exchange.place_scheduled_order(schedule)

        # Update live orders
        for order in Order.select().where(Order.order_id.is_null(False) & Order.is_live):
            if order.credential.exchange == APICredential.EXCHANGE__GEMINI:
                exchange = GeminiExchange(order.credential)                
            else:
                raise Exception(f"Exchange {schedule.exchange} not implemented yet!")

            print(f"Updating Order {order.id}")
            exchange.update_order(order)

        time.sleep(10)



if __name__ == "__main__":
	timer_thread()
