# -*- coding:utf-8 -*-
import numpy as np
from numpy.linalg import inv
from scipy.optimize import minimize_scalar
from scipy.signal import stft, istft


#suppose that the number of sources and microphones are equal.

class ICA:
    
    def __init__(self):
        self.max_iter = 50
        self.eta = 1.0 * 10 ** (-4) # is step size

    def ica(self, x):
        x = np.array(x)
        w = self.__optimize(x)
        y = np.dot(w, x)
        return y, w

    def __fai_func(self, y):
        return 1/(1+np.exp(-y.real)) + 1j*1/(1+np.exp(-y.imag))

    def __alpha(self, y):
        return  np.dot(self.__fai_func(y), y.T.conjugate())    

    def __optimize(self, x):
        r,c = x.shape
        w = np.zeros((r,r), dtype=np.complex64)
        w += np.diag(np.ones(r))
        
        
        for _ in range(self.max_iter):
            y = np.dot(w, x)

            alpha = np.zeros((r,r), dtype=np.complex64)

            for i in range(c):
                alpha += self.__alpha(y[:,i])
            
            alpha = alpha/c
            w += self.eta * np.dot((np.diag(np.diag(alpha)) - alpha),  inv(w.T.conjugate()))
            
        return w
    
class FDICA(ICA):
    '''
    The class FDCIA is inherited from ICA
    '''

    def __init__(self, x, sample_freq, win='boxcar', nperseg=256, noverlap=128, n=3):
        '''
        @param(d): is a vector which represents the distance from a reference point.
        @param(win):str, desired window to use.
        @param(nperseg): length of each segment.
        @param(noverlap): number of points to overlap between segments.
        @param(n): number of sources.
        '''
        super().__init__()
        self.m_shit = 5
        self.x = np.array(x)
        self.sample_freq = sample_freq
        self.win = win
        self.nperseg = nperseg
        self.noverlap = noverlap
        self.n = n

    def fdica(self):
        '''
        X is complex64-type-3-dementional array whose x axis is microphie , y axis is the segment times, z is frequency respectively.
        @output(x_prd): 3 dimensional array whose 1st axis is the source index, 2nd is the microphon index, third is data of them.
        '''

        f,_,X = stft(self.x, self.sample_freq, self.win, self.nperseg, self.noverlap)
        # X is (channel index, freq index, time segment idex)

        Y = self.reconstruct(f,X,self.n)

        _,x_prd = istft(Y, self.sample_freq, self.win, self.nperseg, self.noverlap)
        
        return x_prd


    def reconstruct(self,f,X,n):

        W = np.zeros((n,n,len(f)),dtype=np.complex64)
        Y = np.zeros_like(X)

        #全ての周波数ビンiについて
        for i in range(len(f)):
            _,W[:,:,i] = self.ica(X[:,i,:])

            #directivity pattern の関数Fを作成

#            def F(theta):
#                F = np.zeros(n)
#                for l in range(n):
#                    for k in range(n):
#                        F[l] += W[l,k,i]*np.exp(1j*2*np.pi*f[i]*(k-1)*np.sin(theta)/340)
#                return F
            
            def F0(theta):
                F0 = 0
                for k in range(n):
                    F0 += W[0,k,i]*np.exp(1j*2*np.pi*f[i]*(k-1)*np.sin(theta)/340)
                return F0

            def F1(theta):
                F1 = 0
                for k in range(n):
                    F1 += W[1,k,i]*np.exp(1j*2*np.pi*f[i]*(k-1)*np.sin(theta)/340)
                return F1

            def F2(theta):
                F2 = 0
                for k in range(n):
                    F2 += W[2,k,i]*np.exp(1j*2*np.pi*f[i]*(k-1)*np.sin(theta)/340)
                return F2

            #Fの最適化によりnull directionを探す
            #入力が3の場合について書いています

#            for j in range(3):
#                theta1 = minimize(F[j],x0=-np.pi/3,bounds=np.array(-np.pi/2,-np.pi/6),method='BFGS')
#                theta2 = minimize(F[j],x0=0,bounds=np.array(-np.pi/6,np.pi/6),method="BFGS")
#                theta3 = minimize(F[j],x0=np.pi/3,bounds=np.array(np.pi/6,np.pi/2),method="BFGS")

            b0 = np.array([-np.pi/2,-np.pi/6])
            b1 = np.array([-np.pi/6,np.pi/6])
            b2 = np.array([np.pi/6,np.pi/2])

            theta00 = minimize_scalar(F0,bounds=b0,method="bounded")
            theta01 = minimize_scalar(F0,bounds=b1,method="bounded")
            theta02 = minimize_scalar(F0,bounds=b2,method="bounded")

            theta10 = minimize_scalar(F1,bounds=b0,method="bounded")
            theta11 = minimize_scalar(F1,bounds=b1,method="bounded")
            theta12 = minimize_scalar(F1,bounds=b2,method="bounded")

            theta20 = minimize_scalar(F2,bounds=b0,method="bounded")
            theta21 = minimize_scalar(F2,bounds=b1,method="bounded")
            theta22 = minimize_scalar(F2,bounds=b2,method="bounded")

                #theta1,theta2,theta3のうち、二つは０に近いと考えられる。
                #よってFが最大の方向のインデックスを取れば、音源の方向がわかる。
            k0 = np.argmax(np.array([np.abs(theta00.x),np.abs(theta01.x),np.abs(theta02.x)]))
            k1 = np.argmax(np.array([np.abs(theta10.x),np.abs(theta11.x),np.abs(theta12.x)]))
            k2 = np.argmax(np.array([np.abs(theta20.x),np.abs(theta21.x),np.abs(theta22.x)]))
            
            #Wの0行目を-60度方向の音、1行目を0度方向、2行目を60度方向に入れ替え
            if k0 == 1:
                W[0,:,i],W[1,:,i] = W[1,:,i],W[0,:,i]
            if k0 == 2:
                W[0,:,i],W[2,:,i] = W[2,:,i],W[0,:,i]
            if k1 == 0:
                W[1,:,i],W[0,:,i] = W[0,:,i],W[1,:,i]
            if k1 == 2:
                W[1,:,i],W[2,:,i] = W[2,:,i],W[1,:,i]
            if k2 == 0:
                W[2,:,i],W[0,:,i] = W[0,:,i],W[2,:,i]
            if k2 == 1:
                W[2,:,i],W[1,:,i] = W[1,:,i],W[2,:,i]

            #規格化
            #Fを最小化するところで規格化してしまっているが、音源方向はABFと同じ働きによる音の抑制は少ないと考えられるのでこのまま規格化している
            W[0,:,i] = W[0,:,i]/F0(theta00)
            W[1,:,i] = W[1,:,i]/F1(theta11)
            W[2,:,i] = W[2,:,i]/F2(theta22)

            Y[:,i,:] = np.dot(W,X[:,i,:])
        
        return Y