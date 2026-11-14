# Lecture notes — Feed-forward neural networks

## 1. The neuron
A neuron computes a weighted sum of its inputs plus a bias and passes it through an activation function:
`a = g(w·x + b)`. Without a non-linear `g`, any stack of layers collapses into one linear map, so the network can
only draw linear decision boundaries.

## 2. The multi-layer perceptron (MLP)
Neurons are organised in layers; every neuron of layer *l* is connected to every neuron of layer *l+1*
("fully connected"). Information flows only forward: input → hidden layer(s) → output. For a single hidden layer:

```
h = g(W1 x + b1)        hidden activations
ŷ = σ(W2 h + b2)        output (sigmoid for binary classification)
```

**Universal approximation:** one hidden layer with enough units can approximate any continuous function on a
compact set — but it says nothing about how many units are needed or whether gradient descent will find them.
Depth often gives the same expressiveness with far fewer parameters.

## 3. Activation functions
| Function | Formula | Notes |
|---|---|---|
| Sigmoid | 1 / (1 + e^-z) | Output in (0,1); saturates → gradients ≤ 0.25, vanish in deep nets |
| Tanh | (e^z − e^-z)/(e^z + e^-z) | Zero-centred; still saturates |
| ReLU | max(0, z) | Cheap, no saturation for z > 0; "dead" units if z < 0 always |

Use sigmoid (binary) or softmax (multi-class) at the **output**; prefer ReLU-family in **hidden** layers.

## 4. Loss functions
- Binary cross-entropy: `L = −[y log ŷ + (1−y) log(1−ŷ)]`. With a sigmoid output, `∂L/∂z = ŷ − y`.
- Mean squared error is a poor match for sigmoid outputs (gradients vanish when the prediction is confidently wrong).

## 5. Backpropagation
Backprop is the chain rule applied layer by layer, from the output back to the input, reusing the values cached
in the forward pass. For the network above (batch of m examples):

```
dZ2 = Ŷ − Y
dW2 = (1/m) dZ2 Hᵀ        db2 = mean(dZ2)
dH  = W2ᵀ dZ2
dZ1 = dH ⊙ g'(Z1)
dW1 = (1/m) dZ1 Xᵀ        db1 = mean(dZ1)
```

Always verify with a **gradient check**: compare to `(L(θ+ε) − L(θ−ε)) / 2ε`.

## 6. Training
- **Gradient descent:** `θ ← θ − η ∇L`. Mini-batch SGD trades gradient noise for speed.
- **Learning rate η:** too large → divergence/oscillation; too small → slow. Tune it on the validation set (try a
  log scale: 1, 0.1, 0.01 …).
- **Epoch:** one full pass over the training data.

## 7. Initialisation
- **Never initialise all weights to the same value (e.g. zeros):** every hidden unit then receives the same
  gradient and stays identical forever (symmetry is never broken). Biases can start at zero.
- Xavier/Glorot (tanh, sigmoid): variance `1/n_in`. He (ReLU): variance `2/n_in`.

## 8. Generalisation
- Split data into **train / validation / test**. Fit on train, tune hyper-parameters and early stopping on
  validation, report on test **once**. Using the test set for any decision makes the reported score optimistic.
- **Overfitting:** training loss keeps decreasing while validation loss increases. Remedies: more data, L2 weight
  decay, dropout, early stopping, smaller model.
- High training accuracy alone says nothing about generalisation.
