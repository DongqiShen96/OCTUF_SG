# OCTUF_SG

## Requirements
- Python == 3.8.5
- Pytorch == 1.8.0

## Datasets
- Train data: [400 images](https://drive.google.com/file/d/1hELlT70R56KIM0VFMAylmRZ5n2IuOxiz/view?usp=sharing) from BSD500 dataset
- Test data: Set11, [Urban100](https://drive.google.com/file/d/1cmYjEJlR2S6cqrPq8oQm3tF9lO2sU0gV/view?usp=sharing)

## :OCTUF result
`result_octuf/Set11`

## :Model checkpoint
`/save_OCTUF`

## :computer: Command
### Train
`python train_OCTUF.py --sensing_rate 0.1/0.25/0.3/0.4/0.5`
### Test
`python test_octuf.py --sensing-rate 0.1/0.25/0.3/0.4/0.5 --test_name Set11/Urban100`