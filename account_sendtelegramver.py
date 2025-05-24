import sys
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QHBoxLayout, QDesktopWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from Comms_Class import InitPlusCheck, CpFutureBalance, CpFutureNContract, CpFutureOptionOrder, CpFutureOptionCancel, send_telegram_message

USE_MARKET_PRICE = True


class LogThread(QThread):
    log_signal = pyqtSignal(str, bool)
    use_telegram = True  # 텔레그램 전송 여부 기본값

    def emit_log(self, message, bold=False):
        current_time = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{current_time}] {message}"
        self.log_signal.emit(formatted_message, bold)
        if self.use_telegram:
            send_telegram_message(formatted_message)


class BalanceThread(LogThread):
    def run(self):
        self.emit_log("\n=== 계좌 내역 조회 ===", False)
        objBalance = CpFutureBalance()
        balanceList = []
        if objBalance.request(balanceList):
            if not balanceList:
                self.emit_log("\ud83d\udcdd 현재 보유한 포지션이 없습니다.", False)
                return
            for item in balanceList:
                formatted_items = []
                for k, v in item.items():
                    if k == '평가손익':
                        try:
                            v_int = int(float(v))
                            v_formatted = f"{v_int:,}"
                        except:
                            v_formatted = v
                        color = 'red' if v_int > 0 else 'blue' if v_int < 0 else 'black'
                        formatted_items.append(f"<span style='color:{color}'>[{k}] {v_formatted}</span>")
                    elif k in ['수익률', '평가수익률']:
                        try:
                            v_float = float(v)
                            v_str = f"{v_float:.2f}%"
                        except:
                            v_str = v
                        formatted_items.append(f"[{k}] {v_str}")
                    elif k in ['매입금액', '평가금액']:
                        try:
                            v_int = int(float(v))
                            v_str = f"{v_int:,}"
                        except:
                            v_str = v
                        formatted_items.append(f"[{k}] {v_str}")
                    else:
                        formatted_items.append(f"[{k}] {v}")
                self.emit_log(" | ".join(formatted_items), False)
        else:
            self.emit_log("잔고 조회 실패", False)


class NContractThread(LogThread):
    def run(self):
        self.emit_log("\n=== 미체결 조회 ===", False)
        objNContract = CpFutureNContract()
        nContractList = []
        if objNContract.request(nContractList):
            if not nContractList:
                self.emit_log("\ud83d\udcdd 현재 미체결 주문이 없습니다.", False)
                return
            for item in nContractList:
                details = " | ".join([f"[{k}] {v}" for k, v in item.items()])
                self.emit_log(details, False)
        else:
            self.emit_log("미체결 조회 실패", False)


class ClearThread(LogThread):
    def run(self):
        self.emit_log("\n=== 계좌 내 모든 종목 청산 시작 ===", False)
        objOrder = CpFutureOptionOrder()
        objBalance = CpFutureBalance()
        objNContract = CpFutureNContract()
        objCancel = CpFutureOptionCancel()

        while True:
            self.emit_log("\n\ud83d\udccc 미체결 주문 정리 및 청산 시작...", False)
            try:
                while True:
                    nContractList = []
                    if objNContract.request(nContractList) and nContractList:
                        self.emit_log(f"\ud83d\udea9 미체결 {len(nContractList)}건 발견 → 취소 시도", False)
                        for order in nContractList:
                            order_no = order['주문번호']
                            code = order['코드']
                            qty = order['잔량']

                            if objCancel.cancel_order(order_no, code, qty):
                                self.emit_log(f"\ud83d\udd01 취소 완료: {code} / 주문번호 {order_no}", False)
                            else:
                                self.emit_log(f"⚠️ 취소 실패: {code} / 주문번호 {order_no}", False)
                            time.sleep(1)
                    else:
                        self.emit_log("✅ 모든 미체결 주문 취소 완료", False)
                        break

                balanceList = []
                if objBalance.request(balanceList):
                    if not balanceList:
                        self.emit_log("✅ 모든 포지션 청산 완료!", False)
                        return

                    self.emit_log(f"🔍 현재 잔고 스냅샷 ({len(balanceList)}개 종목):", False)
                    for item in balanceList:
                        self.emit_log(f"    - {item.get('종목명', item.get('코드'))}: 수량 {item['잔고수량']}, 포지션 {item['잔고구분']}", False)

                    for item in balanceList:
                        code = item['코드']
                        qty = item['잔고수량']
                        price = item['현재가'] if USE_MARKET_PRICE else 0
                        position_type = item['잔고구분']

                        if qty <= 0:
                            continue

                        retData = {}
                        if position_type == '매수':
                            success = objOrder.sellOrder(code, price, qty, retData)
                            action = "매도"
                        elif position_type == '매도':
                            success = objOrder.buyOrder(code, price, qty, retData)
                            action = "매수"
                        else:
                            self.emit_log(f"⚠️ 알 수 없는 포지션 타입: {position_type}", False)
                            continue

                        if success:
                            self.emit_log(f"✅ {code} {qty}개 {action} 주문 성공 (가격: {price})", False)
                        else:
                            self.emit_log(f"❌ {code} {qty}개 {action} 주문 실패", False)

            except Exception as e:
                self.emit_log(f"🚨 예외 발생: {e}", True)
            time.sleep(5)


class TradingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("계좌 모니터링")
        self.resize(2400, 600)
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().bottomRight()
        qr.moveBottomRight(cp)
        self.move(qr.topLeft())

        layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        self.balance_btn = QPushButton("계좌 조회")
        self.clear_btn = QPushButton("계좌 전종목 청산")
        self.ncontract_btn = QPushButton("미체결 조회")

        button_layout.addWidget(self.balance_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.ncontract_btn)
        layout.addLayout(button_layout)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
        self.setLayout(layout)

        self.balance_btn.clicked.connect(self.run_balance_thread)
        self.clear_btn.clicked.connect(self.run_clear_thread)
        self.ncontract_btn.clicked.connect(self.run_ncontract_thread)

    def log(self, message, bold=False):
        self.output.append(message)

    def run_balance_thread(self):
        self.balance_thread = BalanceThread()
        self.balance_thread.log_signal.connect(self.log)
        self.balance_thread.start()

    def run_clear_thread(self):
        self.clear_thread = ClearThread()
        self.clear_thread.log_signal.connect(self.log)
        self.clear_thread.start()

    def run_ncontract_thread(self):
        self.ncontract_thread = NContractThread()
        self.ncontract_thread.log_signal.connect(self.log)
        self.ncontract_thread.start()


if __name__ == "__main__":
    if not InitPlusCheck():
        sys.exit()

    app = QApplication(sys.argv)
    ex = TradingApp()
    ex.show()
    sys.exit(app.exec_())