
const AppState = {
    // Получение текущего баланса и данных профиля с бэкенда
    async fetchUserData() {
        try {
            const response = await fetch('/api/user');
            if (!response.ok) {
                throw new Error(`Ошибка сервера: ${response.status}`);
            }
            const data = await response.json();
            
            this.updateBalanceUI(data.balance);
            
            const userNameEl = document.querySelector('.user-name');
            if (userNameEl && data.name) {
                userNameEl.textContent = data.name;
            }

            return data;
        } catch (error) {
            console.error('Не удалось загрузить данные профиля:', error);
        }
    },


    updateBalanceUI(newBalance) {
        const balanceEl = document.getElementById('balance-value');
        if (balanceEl) {
            balanceEl.textContent = newBalance;
        }
    },


    async orderTaxi(price, usePoints = false) {
        try {
            const response = await fetch('/api/taxi/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ price: price, use_points: usePoints })
            });
            const data = await response.json();
            if (data.status === 'success') {
                this.updateBalanceUI(data.new_balance);
            }
            return data;
        } catch (error) {
            console.error('Ошибка заказа такси:', error);
        }
    },

    async orderFood(totalPrice) {
        try {
            const response = await fetch('/api/food/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ total_price: totalPrice })
            });
            const data = await response.json();
            if (data.status === 'success') {
                this.updateBalanceUI(data.new_balance);
            }
            return data;
        } catch (error) {
            console.error('Ошибка оформления заказа еды:', error);
        }
    },


    async claimInvestBonus() {
        try {
            const response = await fetch('/api/invest/claim-bonus', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            if (data.status === 'success') {
                this.updateBalanceUI(data.new_balance);
            }
            return data;
        } catch (error) {
            console.error('Ошибка получения бонуса:', error);
        }
    }
};


document.addEventListener('DOMContentLoaded', () => {
    AppState.fetchUserData();
});