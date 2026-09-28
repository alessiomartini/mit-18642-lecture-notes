# fm_casestudy_1_0.r
#
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
}
# 0.2 Load packages into R session

library("quantmod")  
library("tseries")  
library("vars")  
library("fxregime")  

# 1. Load data into R session ----

#   1.1  Stock Price Data from Yahoo
#         Apply quantmod(sub-package TTR)  function 
#           getYahoodata 
#
#             Returns historical data for any symbol at the website 
#              http://finance.yahoo.com
#
#     1.1.1 Set start and end date for collection in YYYYMMDD (numeric) format
date.start<-20000101
date.end<-20130531


#     1.1.2 Collect historical data for S&P 500 Index
SP500 <- getYahooData("^GSPC", start=date.start, end=date.end)
chartSeries(SP500[,1:5])

#     1.1.3 Collect historical data for 4 stocks
GE <- getYahooData("GE", start=date.start, end=date.end)
BAC <- getYahooData("BAC", start=date.start, end=date.end)
JDSU <- getYahooData("JDSU", start=date.start, end=date.end)
XOM <- getYahooData("XOM", start=date.start, end=date.end)

chartSeries(GE[,1:5])
chartSeries(BAC[,1:5])
chartSeries(JDSU[,1:5])
chartSeries(XOM[,1:5])

#     1.1.4 Details of data object GE from getYahoodata
#
# GE is a matrix object with 
#     row dimension equal to the number of dates 
#     column dimension equal to 9
is.matrix(GE)
dim(GE)
#   Print out the first and last parts of the matrix:
head(GE)
tail(GE)
#   Some attributes of the object GE

mode(GE)  # storage mode of GE is "numeric"
class(GE) # object-oriented class(es) of GE are "xts" and "zoo"
          # xts is an extensible time-series object from the package xts
          # zoo is an object storing ordered observations in a vector or matrix with an index attribute 
              # Important zoo functions
              #   coredata() extracts or replaces core data
              #   index() extracts or replaces the  (sort.by) index of the object

# 1.2 Federal Reserve Economic Data (FRED) from the St. Louis Federal Reserve
#       Apply quantmod  function 
#           getSymbols( seriesname, src="FRED")
#
#             Returns historical data for any symbol at the website
#               http://research.stlouisfed.org/fred2/
#
# Series name | Description
# 
# DGS3MO      | 3-Month Treasury, constant maturity rate
# DGS1        | 1-Year Treasury, constant maturity rate
# DGS5        | 5-Year Treasury, constant maturity rate
# DGS10       | 10-Year Treasury, constant maturity rate
#
# DAAA        | Moody's Seasoned Aaa Corporate Bond Yield 
# DBAA        | Moody's Seasoned Baa Corporate Bond Yield 
#
# DCOILWTICO  | Crude Oil Prices: West Text Intermediate (WTI) - Cushing, Oklahoma
# 
#   1.2.1   Default setting collects entire series
#           and assigns to object of same name as the series
getSymbols("DGS3MO", src="FRED")
getSymbols("DGS1", src="FRED")
getSymbols("DGS5", src="FRED")
getSymbols("DGS10", src="FRED")

getSymbols("DAAA", src="FRED")
getSymbols("DBAA", src="FRED")

getSymbols("DCOILWTICO", src="FRED")

# Each object is a 1-column matrix with time series data
#   The column-name is the same as the object name
is.matrix(DGS3MO) #
dim(DGS3MO)
head(DGS3MO)
tail(DGS3MO)
mode(DGS3MO)
class(DGS3MO)
#
# 2.0   Merge data series together

#   2.1 Create data frame with all FRED series from 2000/01/01 on
# 
#   Useful functions/methods   for zoo objects
#     merge()
#     lag (lag.zoo)
#     diff()
#     window.zoo()
#
#     na.locf() # replace NAs by last previou non-NA
#     rollmean(), rollmax() # compute rolling functions, column-wise

fred.data0<-merge(
  DGS3MO,
  DGS1,
  DGS5,
  DGS10,
  DAAA,
  DBAA,
  DCOILWTICO)["2000::2013-05"]

tail(fred.data0)

# Determine data dimensions
dim(fred.data0)
class(fred.data0)

# Check first and last rows in object
head(fred.data0) ; tail(fred.data0)
# Count the number of NAs in each column
apply(is.na(fred.data0),2,sum)
#  Plot the rates series all togehter
opar<-par()

par(fg="blue",bg="black",
    col.axis="gray",
    col.lab="gray",
    col.main="blue",
    col.sub="blue")

ts.plot(as.ts(fred.data0[,1:6]),col=rainbow(6),bg="black",
        main="FRED Data:  Rates")
par(opar)

# add legend to plot
legend(x=0,y=2, 
       legend=dimnames(fred.data0)[[2]][1:6],
       lty=rep(1,times=6), 
       col=rainbow(6), 
       cex=0.75)
# Plot the Crude Oil PRice
chartSeries(to.monthly(fred.data0[,"DCOILWTICO"]), main="FRED Data: Crude Oil (WTI)")

chartSeries(to.monthly(XOM[,1:5]))


#   2.2 Merge the closing prices for the stock market data series
yahoo.data0<-merge(BAC$Close,
           GE$Close,
           JDSU$Close,
           XOM$Close,
           SP500$Close)
# Replace the index of yahoo data with date values that do not include hours/minutes

dimnames(yahoo.data0)[[2]]<-c("BAC","GE","JDSU","XOM","SP500")
yahoo.data0.0<-zoo(x=coredata(yahoo.data0), order.by=as.Date(time(yahoo.data0)))

# fred.data0 is already indexed by this scale

#   2.3 Merge the yahoo and Fred data together

#     2.3.1 merge with all dates
casestudy1.data0<-merge(yahoo.data0.0, fred.data0)

dim(casestudy1.data0)
head(casestudy1.data0)
tail(casestudy1.data0)
apply(is.na(casestudy1.data0),2,sum)

#     2.3.2 Subset out days when SP500 is not missing (not == NA)

index.notNA.SP500<-which(is.na(coredata(casestudy1.data0$SP500))==FALSE)
casestudy1.data0.0<-casestudy1.data0[index.notNA.SP500,]

head(casestudy1.data0.0)
tail(casestudy1.data0.0)

apply(is.na(casestudy1.data0.0)==TRUE, 2,sum)

# Remaining missing values are for interest rates and the crude oil spot price
#   There are days when the stock market is open but the bond market and/or commodities market
#   is closed 
# For the rates and commodity data, replace NAs with previoius non-NA values
casestudy1.data0.00<-na.locf(casestudy1.data0.0)

apply(is.na(casestudy1.data0.00),2,sum) # Only 1 NA left, the first DCOILWTICO value

save(file="casestudy_1_0.RData", list=ls())

