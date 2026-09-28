# fx_casestudy_fx_1.r
#
# Collect Exchange Rate data from Federal Reserve  Economic Data (FRED)
#   Create time series matrix of FX rates
#   Save r workspace with time series matrix 
#         fred.fxrates.00


#   * Install/load R packages 
#   * Collect historical financial data from internet
#   * Create time series data matrix: casestudy1.data0.0
#         Closing prices on stocks (BAC, GE, JDSU, XOM)
#         Closing values of indexes (SP500)
#         Yields on constant maturity US rates/bonds (3MO, 1YR, 5YR, 10 YR)
#         Closing price on crude oil spot price
# 0. Install and load packages ----
#
# 0.1 Install packages ---
#     Set ind.install0 to TRUE if running script for first time on a computer
#     or updating the packages
ind.install0<-FALSE
#
if (ind.install0){
  install.packages("quantmod") 
  install.packages("tseries") 
  install.packages("vars")
  install.packages("fxregime")
  install.packages("moments")
}
# 0.2 Load packages into R session

library("quantmod")  
library("tseries")  
library("vars")  
library("fxregime")  
library("moments")  
#  1.0 Collect data from FRED

options(stringsAsFactors=FALSE)

# 1.1 Read documentation file for FRED fx series data ----
# 
fred.fxrates<-read.csv(file="fred_fxrates.txt",sep=";", 
                       header=TRUE,
                       stringsAsFactors=FALSE,
                       strip.white=TRUE)
dimnames(fred.fxrates)[[2]]

fred.fxrates.symbol0<-substring(fred.fxrates[,'filename'], first=1, last=nchar(fred.fxrates[,'filename']) -4)

fred.fxrates.doc<-data.frame(symbol0=fred.fxrates.symbol0, fred.fxrates)
fred.fxrates.doc<-fred.fxrates.doc[1:23,]
dim(fred.fxrates.doc)
head(fred.fxrates.doc)
tail(fred.fxrates.doc)
# Apply to each rate in 

# 1.2 Collect all symbol data ----
#    sample code:
#     getSymbols("DEXJPUS",src="FRED") # FX rates from FRED 
#

for (symbol0 in fred.fxrates.doc[,"symbol0"]){
  print(symbol0)
  getSymbols(symbol0,src="FRED") # FX rates from FRED 
}

# 1.3 Merge all time series and subset days when EUR/USD available ----
mergecommand0<-paste("merge(",
                     paste(fred.fxrates.doc[,"symbol0"],collapse=","),
                     ")", collapse="")

fred.fxrates.0<-eval(parse(text=mergecommand0))
dim(fred.fxrates.0)
head(fred.fxrates.0)
tail(fred.fxrates.0)

# Subset out only days when EURO is available 
fred.fxrates.00<-fred.fxrates.0[ is.na(fred.fxrates.0[,'DEXUSEU']) == FALSE,]
dim(fred.fxrates.00)
head(fred.fxrates.00)
tail(fred.fxrates.00)

save(file="fm_casestudy_fx_1.Rdata", list=ls())

