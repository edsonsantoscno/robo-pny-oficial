# 🚀 CopyTrader PNY - Robô de Trading Automático com Copy Trading

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green)](https://flask.palletsprojects.com/)
[![Binance API](https://img.shields.io/badge/Binance-API-yellow)](https://binance-docs.github.io/apidocs/)
[![License MIT](https://img.shields.io/badge/License-MIT-red)](LICENSE)

**CopyTrader PNY** é um sistema completo de **trading automático com copy trading** que permite:
- 🤖 **Robô Mestre** - Opera automaticamente com múltiplas estratégias
- 👥 **Robô Cliente** - Copia automaticamente os trades do mestre
- 📊 **Dashboard SaaS** - Interface web profissional em tempo real
- 🎯 **Múltiplas Estratégias** - EMA_ONLY, EMA_SCALP, RSI, PNY
- 💰 **Gerenciamento de Risco** - Stop Loss, Take Profit, Limite de Perda Diária

---

## 📋 **Índice**

- [Características](#características)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Como Usar](#como-usar)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [API Endpoints](#api-endpoints)
- [Estratégias](#estratégias)
- [Troubleshooting](#troubleshooting)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

---

## ✨ **Características**

### 🤖 **Robô Mestre**
- ✅ Trading automático 24/7
- ✅ Múltiplas estratégias (EMA, RSI, PNY)
- ✅ Gerenciamento automático de risco
- ✅ Sincronização com clientes via Supabase
- ✅ Logs detalhados de operações

### 👥 **Robô Cliente**
- ✅ Cópia automática de trades do mestre
- ✅ Gerenciamento de API Keys (criptografado)
- ✅ Modo automático/manual/pausado
- ✅ Sincronização em tempo real
- ✅ Histórico de trades

### 📊 **Dashboard SaaS**
- ✅ Interface web moderna e responsiva
- ✅ Atualização em tempo real (5s)
- ✅ Gráficos animados (Chart.js)
- ✅ Controle de parâmetros (SL, TP, %)
- ✅ Notificações em tempo real

### 🎯 **Estratégias de Trading**
- **EMA_ONLY** - Cruzamento de EMA 9/21
- **EMA_SCALP** - Scalping em pullback
- **RSI** - Sobrecompra/Sobrevenda
- **PNY** - Estratégia proprietária com Stochastic

---

## 📦 **Requisitos**

