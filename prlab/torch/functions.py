import torch


def make_theta_from_st(st, is_inverse=False):
    """
    ST without rotate
    note: batch mode [-1, 4] to [-1, 2, 3]
    e[1], e[3] in ratio, scale mode (mean not need *2/w or *2/h)

    ref: https://discuss.pytorch.org/t/how-to-convert-an-affine-transform-matrix-into-theta-to-use-torch-nn-functional-affine-grid/24315/3

    theta[0,0] = param[0,0]
    theta[0,1] = param[0,1]*h/w
    theta[0,2] = param[0,2]*2/w + theta[0,0] + theta[0,1] - 1
    theta[1,0] = param[1,0]*w/h
    theta[1,1] = param[1,1]
    theta[1,2] = param[1,2]*2/h + theta[1,0] + theta[1,1] - 1

    TODO make sure none zero for all 4 number, or replace with very small values
    :param st: [[sx, tx, sy, ty]] (omit 2 zeros) st_size
    :param is_inverse: return matrix or inverse of matrix
    :return: [[sx, 0, tx], [0, sy, ty]] or [[1/sx, 0, -tx/sx], [0, 1/sy, -ty/sy]] (reverse)
    """
    zero_vec = torch.zeros(st.size()[0], dtype=torch.float)
    if st.get_device() >= 0:
        zero_vec = zero_vec.to(device=st.get_device())

    o = [st[:, 0], zero_vec, st[:, 1], zero_vec, st[:, 2], st[:, 3]]

    if is_inverse:
        o = [1 / st[:, 0], zero_vec, -st[:, 1] / st[:, 0], zero_vec, 1 / st[:, 2], -st[:, 3] / st[:, 2]]
    theta = torch.stack(o, dim=-1)

    theta[:, 2] = theta[:, 2] + theta[:, 0] + theta[:, 1] - 1
    theta[:, 5] = theta[:, 5] + theta[:, 3] + theta[:, 4] - 1

    return theta.view(-1, 2, 3)


def soft_argmax(x=None):
    """
    Implement soft-argmax, that can differentiable.
    ```
        soft_argmax(torch.Tensor([[1.1, 3.0, 1.1, 1.3, 0.8]]))
    ```
    implement in batch size
    ref: https://medium.com/@nicolas.ugrinovic.k/soft-argmax-soft-argmin-and-other-soft-stuff-7f94e6120dff
    :param x: [-1, size], if x more than 2, then convert to 2 and calc argmax, and then convert back (by row, col)
    :return: max[-1], argmax[-1]
    """
    beta = 12
    a = torch.exp(beta * x)
    b = torch.sum(torch.exp(beta * x), dim=-1)
    soft_max = a / b.unsqueeze(dim=-1)
    max_val = torch.sum(soft_max * x, dim=-1)
    pos = torch.arange(0, x.size()[-1])
    s_argmax = torch.sum(soft_max * pos, dim=-1)
    return max_val, s_argmax


def build_grid(source_size, target_size):
    """
    ref: https://discuss.pytorch.org/t/cropping-a-minibatch-of-images-each-image-a-bit-differently/12247/5
    if w != h then need change small thing
    :param source_size:
    :param target_size:
    :return:
    """
    k = float(target_size) / float(source_size)
    direct = torch.linspace(-k, k, target_size).unsqueeze(0).repeat(target_size, 1).unsqueeze(-1)
    full = torch.cat([direct, direct.transpose(1, 0)], dim=2).unsqueeze(0)
    return full


def random_crop_grid(x, grid):
    delta = x.size(2) - grid.size(1)
    grid = grid.repeat(x.size(0), 1, 1, 1)
    # Add random shifts by x
    grid[:, :, :, 0] = grid[:, :, :, 0] + \
                       torch.FloatTensor(x.size(0)).random_(0, delta) \
                           .unsqueeze(-1).unsqueeze(-1).expand(-1, grid.size(1), grid.size(2)) / x.size(2)
    # Add random shifts by y
    grid[:, :, :, 1] = grid[:, :, :, 1] + \
                       torch.FloatTensor(x.size(0)).random_(0, delta) \
                           .unsqueeze(-1).unsqueeze(-1).expand(-1, grid.size(1), grid.size(2)) / x.size(2)
    return grid

# # We want to crop a 80x80 image randomly for our batch
# # Building central crop of 80 pixel size
# grid_source = build_grid(batch.size(2), 80)
# # Make radom shift for each batch
# grid_shifted = random_crop_grid(batch, grid_source)
# # Sample using grid sample
# sampled_batch = F.grid_sample(batch, grid_shifted)
