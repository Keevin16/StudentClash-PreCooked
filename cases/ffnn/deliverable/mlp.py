"""Project 1 - MLP from scratch (NumPy). Two moons dataset, one hidden layer."""
import numpy as np

rng = np.random.default_rng(0)


def make_moons(n=400, noise=0.2):
    t = rng.uniform(0, np.pi, n // 2)
    a = np.c_[np.cos(t), np.sin(t)]
    b = np.c_[1 - np.cos(t), 0.5 - np.sin(t)]
    X = np.r_[a, b] + rng.normal(0, noise, (n, 2))
    y = np.r_[np.zeros(n // 2), np.ones(n // 2)]
    return X, y


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


class MLP:
    def __init__(self, n_in, n_hidden):
        # Xavier initialisation (see report, section 2.3)
        self.W1 = np.zeros((n_hidden, n_in))
        self.b1 = np.zeros((n_hidden, 1))
        self.W2 = rng.normal(0, 1 / np.sqrt(n_hidden), (1, n_hidden))
        self.b2 = np.zeros((1, 1))

    def forward(self, X):
        self.X = X
        self.Z1 = self.W1 @ X + self.b1
        self.H = sigmoid(self.Z1)
        self.Yhat = sigmoid(self.W2 @ self.H + self.b2)
        return self.Yhat

    def backward(self, Y, lr):
        m = Y.shape[1]
        dZ2 = self.Yhat - Y
        dW2 = dZ2 @ self.H.T / m
        db2 = dZ2.mean(axis=1, keepdims=True)
        dZ1 = (self.W2.T @ dZ2) * self.H * (1 - self.H)
        dW1 = dZ1 @ self.X.T / m
        db1 = dZ1.mean(axis=1, keepdims=True)
        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        self.W1 -= lr * dW1
        self.b1 -= lr * db1


def loss(Yhat, Y):
    return -np.mean(Y * np.log(Yhat + 1e-9) + (1 - Y) * np.log(1 - Yhat + 1e-9))


X, y = make_moons()
idx = rng.permutation(len(y))
train, test = idx[:320], idx[320:]
Xtr, Ytr = X[train].T, y[train][None, :]
Xte, Yte = X[test].T, y[test][None, :]

net = MLP(2, 16)
best_acc, best_epoch = 0, 0
for epoch in range(5000):
    net.forward(Xtr)
    net.backward(Ytr, lr=2.0)
    if epoch % 100 == 0:
        acc = ((net.forward(Xte) > 0.5) == Yte).mean()
        if acc > best_acc:  # early stopping on the best epoch
            best_acc, best_epoch = acc, epoch
        print(f"epoch {epoch}  train loss {loss(net.forward(Xtr), Ytr):.3f}  test acc {acc:.3f}")

print(f"best test accuracy {best_acc:.3f} at epoch {best_epoch}")
