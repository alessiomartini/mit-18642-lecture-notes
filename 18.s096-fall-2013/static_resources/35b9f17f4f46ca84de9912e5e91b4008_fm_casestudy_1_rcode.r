# fm_casestudy_1_rcode.r

#Execute the R-script ``fm\_casestudy\_1\_0.r'' 
#   creates the time-series matrix $casestudy1.data0.00$ 
#     and saves it in R-workspace ``casestudy_1_0.Rdata'.

#source("fm_casestudy_1_0.r")


library("zoo")
load("casestudy_1_0.RData")
dim(casestudy1.data0.00)
names(casestudy1.data0.00)
head(casestudy1.data0.00)
tail(casestudy1.data0.00)

# We first plot the raw data for the stock $GE$, the market-portfolio index $SP500,$ and the risk-free interest rate.

library ("graphics")
library("quantmod")
plot(casestudy1.data0.00[,"GE"],ylab="Price",main="GE Stock")

plot(casestudy1.data0.00[,"SP500"], ylab="Value",main="S&P500 Index")

plot(casestudy1.data0.00[,"DGS3MO"], ylab="Rate" ,
     main="3-Month Treasury Rate (Constant Maturity)")


#Now we construct the variables with the log daily returns of GE and the SP500 index as well as the risk-free asset returns

# Compute daily log returns of GE stock
r.daily.GE<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"GE"]))), 
                 order.by=time(casestudy1.data0.00)[-1])
dimnames(r.daily.GE)[[2]]<-"r.daily.GE"
dim(r.daily.GE)
head(r.daily.GE)

# Compute daily log returns of the SP500 index
r.daily.SP500<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"SP500"]))),
                    order.by=time(casestudy1.data0.00)[-1])
dimnames(r.daily.SP500)[[2]]<-"r.daily.SP500"
dim(r.daily.SP500)
head(r.daily.SP500)

# Compute daily return of the risk-free asset 
#     accounting for the number of days between successive closing prices
#     apply annual interest rate using 360 days/year (standard on 360-day yearsince the previous close)

r.daily.riskfree<-log(1 + .01*coredata(casestudy1.data0.00[-1,"DGS3MO"]) *
                        diff(as.numeric(time(casestudy1.data0.00)))/360)
dimnames(r.daily.riskfree)[[2]]<-"r.daily.riskfree"

# Compute excess returns (over riskfree rate)

r.daily.GE.0<-r.daily.GE - r.daily.riskfree
  dimnames(r.daily.GE.0)[[2]]<-"r.daily.GE.0"

r.daily.SP500.0<-r.daily.SP500 - r.daily.riskfree
  dimnames(r.daily.SP500.0)[[2]]<-"r.daily.SP500.0"

# Merge all the time series together,
#     and display first and last sets of rows
r.daily.data0<-merge(r.daily.GE, r.daily.SP500, r.daily.riskfree, 
                     r.daily.GE.0, r.daily.SP500.0)

head(r.daily.data0)
tail(r.daily.data0)

#Now we plot the excess returns of GE vs those of the SP500:

plot(r.daily.SP500.0, r.daily.GE.0)
abline(h=0,v=0)


# Fitting the Linear Regression for CAPM ----

#The linear regression model is fit using the R-function lm():

options(show.signif.stars=FALSE)

lmfit0<-lm(r.daily.GE.0 ~ r.daily.SP500.0, data=r.daily.data0)
  names(lmfit0) #element names of list object lmfit0
  summary.lm(lmfit0) #function summarizing objects created by lm()


lmfit0.summary<-summary(lmfit0)
tstat.intercept<-round(lmfit0.summary$coefficients["(Intercept)", "t value"],digits=4)

# Note that the $t$-statistic for the intercept $\alpha_{GE}$ is not significant:
print(tstat.intercept)

# Regression Diagnostics ----
#   Some useful R functions

#   anova.lm():  conduct an Analysis of Variance for the linear regression model, detailing the computation of the F-statistic for no regression structure.

#   influence.measures():  compute regression diagnostics evaluating case influence for the linear regression model; includes `hat' matirx, case-deletion statistics for the regression coefficients and for the residual standard deviation.


# Compute influence measures (case-deletion statistics)
lmfit0.inflm<-influence.measures(lmfit0)
names(lmfit0.inflm)
dim(lmfit0.inflm$infmat)
head(lmfit0.inflm$infmat)
head(lmfit0.inflm$is.inf)
# Table counts of influential/non-influential cases
# as measured by the hat/leverage statistic.
table(lmfit0.inflm$is.inf[,"hat"])

# Re-Plot data adding
#     fitted regression line
#     selective highlighting of influential cases

plot(r.daily.SP500.0, r.daily.GE.0,
     main="GE vs SP500 Data \n OLS Fit (Green line)\n High-Leverage Cases (red points)\n High Cooks Dist (blue Xs)", cex.main=0.8)
abline(h=0,v=0)
abline(lmfit0, col=3, lwd=3)

# Plot cases with high leverage as red (col=2) "o"s
index.inf.hat<-which(lmfit0.inflm$is.inf[,"hat"]==TRUE)
points(r.daily.SP500.0[index.inf.hat], r.daily.GE.0[index.inf.hat], 
        col=2, pch="o")

# Plot cases with high cooks distance as big (cex=2) blue (col=4) "X"s
index.inf.cook.d<-which(lmfit0.inflm$is.inf[,"cook.d"]==TRUE)
points(r.daily.SP500.0[index.inf.cook.d], r.daily.GE.0[index.inf.cook.d], 
       col=4, pch="X", cex=2.)

# Plot leverage of cases (diagonals of hat matrix)
lmfit0.leverages<-zoo(lmfit0.inflm$infmat[,"hat"], order.by=time(r.daily.SP500.0))
chartSeries(lmfit0.leverages)

# Note the cases are time points of the time series data
#   The financial crisis of 2008 is evident 

#The R function $plot.lm()$ generates a useful 2x2 display of plots for various regression diagnostic statistics:

layout(matrix(c(1,2,3,4),2,2)) # optional 4 graphs/page 
plot(lmfit0)


# Adding Macro-economic Factors to CAPM ----
# This section sets up the data frame  
# Compute daily log returns of GE stock
r.daily.GE<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"GE"]))), order.by=time(casestudy1.data0.00)[-1])
dimnames(r.daily.GE)[[2]]<-"r.daily.GE"
#dim(r.daily.GE)
#head(r.daily.GE)

# Repeat for stocks BAC, JDSU, XOM and for commodity DCOILWTICO

# Compute daily log returns of BAC stock
r.daily.BAC<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"BAC"]))), order.by=time(casestudy1.data0.00)[-1])
dimnames(r.daily.BAC)[[2]]<-"r.daily.BAC"

# Compute daily log returns of JDSU stock
r.daily.JDSU<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"JDSU"]))), order.by=time(casestudy1.data0.00)[-1])
dimnames(r.daily.JDSU)[[2]]<-"r.daily.JDSU"

# Compute daily log returns of XOM stock
r.daily.XOM<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"XOM"]))), order.by=time(casestudy1.data0.00)[-1])
dimnames(r.daily.XOM)[[2]]<-"r.daily.XOM"

# Compute daily log returns of DCOILWTICO (Crude Oil WTI)
r.daily.DCOILWTICO<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"DCOILWTICO"]))), order.by=time(casestudy1.data0.00)[-1])
dimnames(r.daily.DCOILWTICO)[[2]]<-"r.daily.DCOILWTICO"

# Compute daily log returns of the SP500 index
r.daily.SP500<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"SP500"]))), order.by=time(casestudy1.data0.00)[-1])
dimnames(r.daily.SP500)[[2]]<-"r.daily.SP500"


# Compute daily log change interest rate variables
dlog.daily.DGS1<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"DGS1"]))), 
                      order.by=time(casestudy1.data0.00)[-1])
dimnames(dlog.daily.DGS1)[[2]]<-"dlog.daily.DGS1"

dlog.daily.DGS10<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"DGS10"]))), 
                      order.by=time(casestudy1.data0.00)[-1])
dimnames(dlog.daily.DGS10)[[2]]<-"dlog.daily.DGS10"

dlog.daily.DAAA<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"DAAA"]))), 
                       order.by=time(casestudy1.data0.00)[-1])
dimnames(dlog.daily.DAAA)[[2]]<-"dlog.daily.DAAA"

dlog.daily.DBAA<-zoo( x=as.matrix(diff(log(casestudy1.data0.00[,"DBAA"]))), 
                      order.by=time(casestudy1.data0.00)[-1])
dimnames(dlog.daily.DBAA)[[2]]<-"dlog.daily.DBAA"

# Compute daily return of the risk-free asset (accounting for the number of days since the previous close)

r.daily.riskfree<-log(1 + .01*coredata(casestudy1.data0.00[-1,"DGS3MO"]) *
                        diff(as.numeric(time(casestudy1.data0.00)))/360)
dimnames(r.daily.riskfree)[[2]]<-"r.daily.riskfree"

# Compute excess returns (over riskfree rate)

r.daily.GE.0<-r.daily.GE - r.daily.riskfree
  dimnames(r.daily.GE.0)[[2]]<-"r.daily.GE.0"

r.daily.BAC.0<-r.daily.BAC - r.daily.riskfree
dimnames(r.daily.BAC.0)[[2]]<-"r.daily.BAC.0"

r.daily.JDSU.0<-r.daily.JDSU - r.daily.riskfree
dimnames(r.daily.JDSU.0)[[2]]<-"r.daily.JDSU.0"

r.daily.XOM.0<-r.daily.XOM - r.daily.riskfree
dimnames(r.daily.XOM.0)[[2]]<-"r.daily.XOM.0"

r.daily.SP500.0<-r.daily.SP500 - r.daily.riskfree
  dimnames(r.daily.SP500.0)[[2]]<-"r.daily.SP500.0"

r.daily.DCOILWTICO.0<-r.daily.DCOILWTICO - r.daily.riskfree
dimnames(r.daily.DCOILWTICO.0)[[2]]<-"r.daily.DCOILWTICO.0"

# Merge all the time series together, and display first and last sets of rows
r.daily.data0<-merge(r.daily.GE, r.daily.SP500, r.daily.riskfree, r.daily.GE.0, r.daily.SP500.0)

r.daily.data00<-merge(
  r.daily.GE, r.daily.SP500, r.daily.riskfree, r.daily.GE.0, r.daily.SP500.0,r.daily.DCOILWTICO.0,
  r.daily.BAC, r.daily.JDSU, r.daily.XOM,
  r.daily.BAC.0, r.daily.JDSU.0, r.daily.XOM.0,
  dlog.daily.DGS1, dlog.daily.DGS10, dlog.daily.DAAA, dlog.daily.DBAA)

print(names(r.daily.data00))

#The CAPM relates a stock's return to that of the diversified market portfolio,
# proxied here by the S\&P 500 Index.
#A stock's return can depend on macro-economic factors, such commodity prices, interest rates, economic growth (GDP).


# The linear regression for the simple CAPM:
lmfit0<-lm( r.daily.GE.0 ~ r.daily.SP500.0 , data=r.daily.data00)
summary.lm(lmfit0)

# The linear regression for the extended CAPM:
lmfit1<-lm( r.daily.GE.0 ~ r.daily.SP500.0 + r.daily.DCOILWTICO, data=r.daily.data00)
summary.lm(lmfit1)


# The regression coefficient for the oil factor ($r.daily.DCOILWTICO$)  is 
#   statistically significant and negative.  
#   Over the analysis period, price changes in GE stock are negatively related to the price changes in oil.


#%% anova.lm(lmfit1)
#%% anova.lm(lmfit0)

#  Consider the corresponding models for the oil stock XOM (Exxon-Mobil)

# The linear regression for the simple CAPM:
lmfit0<-lm( r.daily.XOM.0 ~ r.daily.SP500.0 , data=r.daily.data00)
summary.lm(lmfit0)

# The linear regression for the extended CAPM:
lmfit1<-lm( r.daily.XOM.0 ~ r.daily.SP500.0 + r.daily.DCOILWTICO.0, data=r.daily.data00)
summary.lm(lmfit1)

# The R-squared for $XOM$ is lower than for $GE$.  Its relationship to the market index is less strong.

# The beta of XOM with the SP500 is less than 1
# 
#  The regression coefficient for the oil factor ($r.daily.DCOILWTICO$) is 
#    statistically significant and positive.

#For the extended model, we use the R function $plot.lm()$ to display regression diagnostic statistics:

layout(matrix(c(1,2,3,4),2,2)) # optional 4 graphs/page 
plot(lmfit1)

#The high-leverage cases in the data are those which have high Mahalanobis distance from the center of the data in terms of the column space of the independent variables (see Regression Analysis Problem Set).

#We display the data in terms of the independent variables and highlight the high-leverage cases.

# Refit the model using argument x=TRUE so that the lm object includes the
# matrix of independent variables
lmfit1<-lm(r.daily.XOM.0 ~ r.daily.SP500.0 + r.daily.DCOILWTICO,
           data=r.daily.data00,
           x=TRUE)
names(lmfit1)
dim(lmfit1$x)
head(lmfit1$x)

#We now  compute the leverage (and other influence measures) with the function $influence.measures()$
#and display the scatter plot of the independent variables, highlighting the high-leverage cases.


lmfit1.inflm<-influence.measures(lmfit1)
index.inf.hat<-which(lmfit1.inflm$is.inf[,"hat"]==TRUE)

par(mfcol=c(1,1))
plot(lmfit1$x[,2], lmfit1$x[,3],xlab="r.daily.SP500.0", ylab="r.daily.DCOILWTICO.0")
title(main="Scatter Plot of Independent Variables \n High Leverage Points (red o s)")

points(lmfit1$x[index.inf.hat,2], lmfit1$x[index.inf.hat,3],
       col=2,
       pch="o")


